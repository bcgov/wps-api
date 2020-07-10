""" This is a bot to pull hourly weather actuals from the BC FireWeather Phase 1 API
for each weather station and store the results (from a CSV file) in our database.
"""
import os
import json
import logging
from datetime import datetime, timedelta
import re
import asyncio
from typing import List, Dict
from abc import abstractmethod, ABC
from requests import Session
from requests_ntlm import HttpNtlmAuth
import pytz
import pandas as pd
import config
from schemas import WeatherStation
from db.database import ENGINE


LOGGER = logging.getLogger(__name__)

TEMP_CSV_FILENAME = 'weather_station_forecasts.csv'

dirname = os.path.dirname(__file__)
weather_stations_file_path = os.path.join(
    dirname, 'data/weather_stations.json')


# pylint: disable=too-few-public-methods, broad-except
class BuildQuery(ABC):
    """ Base class for building query urls and params """

    def __init__(self):
        """ Initialize object """
        self.base_url = config.get('BC_FIRE_WEATHER_BASE_URL')

    @abstractmethod
    def query(self) -> [str, dict]:
        """ Return query url and params """

# pylint: disable=too-few-public-methods
class BuildQueryByStationCode(BuildQuery):
    """ Class for building a url and params to request a list of stations by code """

    def __init__(self, station_codes: List[int]):
        """ Initialize object """
        super().__init__()
        self.querystring = ''
        for code in station_codes:
            if len(self.querystring) > 0:
                self.querystring += ' or '
            self.querystring += 'stationCode=={}'.format(code)

    def query(self) -> [str, dict]:
        """ Return query url and params for a list of stations """
        params = {'query': self.querystring}
        url = '{base_url}Scripts/Public/Common/Results_Report.asp'.format(base_url=self.base_url)
        return [url, params]

async def _authenticate_session(session: Session) -> Session:
    """ Authenticate the session using NTLM auth
    """
    password = config.get('BC_FIRE_WEATHER_SECRET')
    user = config.get('BC_FIRE_WEATHER_USER')
    auth_url = config.get('BC_FIRE_WEATHER_BASE_URL')
    session.get(auth_url, auth=HttpNtlmAuth('idir\\'+user, password))
    return session

def prepare_fetch_noon_forecasts_query():
    """ Prepare url and params to fetch forecast noon-time values from the BC FireWeather Phase 1 API.
    """
    base_url = config.get('BC_FIRE_WEATHER_BASE_URL')
    start_date = _get_start_date()
    end_date = _get_end_date()
    LOGGER.debug('requesting forecasts from %s to %s', start_date, end_date)
    # Prepare query params and query:
    request_body = {
        'Start_Date': int(start_date),
        'End_Date': int(end_date),
        'Format': 'CSV',
        'cboFilters': config.get('BC_FIRE_WEATHER_FILTER_ID'),
        'rdoReport': 'OSBD',
    }
    endpoint = ('Scripts/Public/Common/Results_Report.asp')
    url = '{base_url}{endpoint}'.format(
        base_url=base_url,
        endpoint=endpoint)
    return url, request_body

async def fetch_noon_forecasts(
        session: Session):
    """ Fetch daily weather forecasts (noon values) for a given station.
    """
    url, request_body = prepare_fetch_noon_forecasts_query()
    # Get forecasts
    response = session.post(url, data=request_body)
    pattern = re.compile(r"fire_weather\/csv\/.+\.csv")
    BC_FIRE_WEATHER_CSV_URL = pattern.search(response.text)   # pylint: disable=invalid-name
    LOGGER.info('Fetching CSV from %s', BC_FIRE_WEATHER_CSV_URL.group(0))
    return BC_FIRE_WEATHER_CSV_URL.group(0)

async def get_csv(
        session: Session,
        csv_url: str):
    """ Fetch CSV of hourly actual weather for a station.
    """
    url = config.get('BC_FIRE_WEATHER_BASE_URL') + csv_url
    response = session.get(
        url,
        auth=HttpNtlmAuth('idir\\'+config.get('BC_FIRE_WEATHER_USER'), config.get('BC_FIRE_WEATHER_SECRET'))
    )
    content = response.content

    # Need to write response content to a CSV file - once the CSV file has been read, it will be deleted
    csv_file = open(TEMP_CSV_FILENAME, 'wb')
    csv_file.write(content)
    csv_file.close()

async def get_noon_forecasts():
    """ Send POST request to BC FireWeather API to generate a CSV,
    then send GET request to retrieve the CSV,
    then parse the CSV and store in DB.
    """
    with Session() as session:
        session = await _authenticate_session(session)
        # Submit the POST request to query forecasts for the station
        csv_url = await fetch_noon_forecasts(session)
        # Use the returned URL to fetch the CSV data for the station
        await get_csv(session, csv_url)
        # Parse the CSV data
        parse_csv()
        LOGGER.debug('Finished writing forecasts to database')

def parse_csv():
    """ Given a CSV of forecast noon-time weather data for a station, load the CSV into a
    pandas dataframe, then insert the dataframe into the DB. (This 2-step process is
    the neatest way to write CSVs into a DB.)
    """
    with open(TEMP_CSV_FILENAME, 'r') as csv_file:
        data_df = pd.read_csv(csv_file)
    station_codes = _get_station_names_to_codes()
    # replace 'display_name' column (station name) in df with station_id
    # and rename the column appropriately
    data_df['display_name'].replace(station_codes, inplace=True)
    data_df.rename(columns={'display_name': 'station_code'}, inplace=True)
    # the CSV created by the FireWeather API contains a column indicating if the data
    # is a forecast or an actual value. All rows in our requested CSV should be forecasts,
    # but to make sure, we drop any rows that contain actuals instead of forecasts
    index_names = data_df[data_df['status'] == 'actual'].index
    data_df.drop(index_names, inplace=True)
    # can now delete the 'status' column entirely, since we know it's all forecasts
    # and we don't want to write this column to the DB
    data_df.drop(['status'], axis=1, inplace=True)
    # weather_date is formatted yyyymmdd as an int - need to reformat it as a Date
    data_df['weather_date'] = pd.to_datetime(data_df['weather_date'], format='%Y%m%d')
    # delete the temp CSV file - it's not needed anymore
    os.remove(TEMP_CSV_FILENAME)
    # write to database using ENGINE connection
    data_df.to_sql('noon_forecasts', con=ENGINE, index=False, if_exists='append')


def _get_now():
    """ Helper function to get the current time (easy function to mock out in testing) """
    return datetime.now(tz=pytz.utc)

def _get_start_date():
    """ Helper function to get the start date for query (if morning run, use current day; if evening run,
    use tomorrow's date, since we only want forecasts, not actuals)
    Strip out time, we just want yyyymmdd """
    date = ''
    now = _get_now()
    pacific_time = datetime.now(tz=pytz.timezone('Canada/Pacific'))
    if pacific_time.hour < 11:
        date = now
    else:
        date = now + timedelta(days=1)  # use tomorrow's date
    return date.strftime('%Y%m%d')

def _get_end_date():
    """ Helper function to get the end date for query (5 days in future).
    Strip out time, we just want <year><month><date> """
    five_days_ahead = _get_now() + timedelta(days=5)
    return five_days_ahead.strftime('%Y%m%d')

def _get_stations_local() -> List[WeatherStation]:
    """ Get list of stations from local json files.
    """
    with open(weather_stations_file_path) as weather_stations_file:
        json_data = json.load(weather_stations_file)
        return json_data['weather_stations']

def _get_station_names_to_codes() -> Dict:
    """ Helper function to create dictionary of (station_name: station_code) key-value pairs
    Is used when replacing station names with station IDs in dataframe
    """
    station_data = _get_stations_local()
    station_codes = {}
    for station in station_data:
        station_codes[station['name']] = station['code']
    # have to hack this, because BC FireWeather API spells a certain station 'DARCY'
    # while our weather_stations.json spells the station 'D'ARCY'
    station_codes['DARCY'] = station_codes.pop('D\'ARCY')
    return station_codes

async def main():
    """ Makes the appropriate method calls in order to submit a query to the BC FireWeather Phase 1 API
    to get (up to) 5-day forecasts for all weather stations, downloads the resulting CSV file, writes
    the CSV file to the database, then deletes the local copy of the CSV file.
    """
    LOGGER.debug('Retrieving noon forecasts...')
    try:
        await get_noon_forecasts()
        LOGGER.debug('Finished retrieving noon forecasts for all weather stations.')
    except Exception as exception:
        LOGGER.error('Failed to retrieve noon forecasts.')
        LOGGER.error(exception)

asyncio.run(main())
