""" This is a bot to pull hourly weather actuals from the BC FireWeather Phase 1 API
for each weather station and store the results (from a CSV file) in our database.
"""
import os
import json
import logging
import pytz
import re
import pandas as pd
from abc import abstractmethod, ABC
from datetime import datetime, timedelta
import math
from typing import List
from aiohttp import ClientSession, BasicAuth, TCPConnector
import config
from schemas import WeatherStation, WeatherStationHourlyReadings, WeatherReading


LOGGER = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)
weather_stations_file_path = os.path.join(
    dirname, 'data/weather_stations.json')


# pylint: disable=too-few-public-methods
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

    def query(self, page) -> [str, dict]:
        """ Return query url and params for a list of stations """
        params = {'query': self.querystring}
        url = '{base_url}/v1/stations/rsql'.format(base_url=self.base_url)
        return [url, params]

async def _fetch_access_token(session: ClientSession) -> dict:
    """ Fetch an access token for BC FireWeather Phase 1 API
    """
    LOGGER.debug('fetching access token...')
    password = config.get('BC_FIRE_WEATHER_SECRET')
    user = config.get('BC_FIRE_WEATHER_USER')
    auth_url = config.get('BC_FIRE_WEATHER_BASE_URL')
    async with session.get(auth_url, auth=BasicAuth(login=user, password=password)) as response:
        return await response.json()

async def _get_auth_header(session: ClientSession) -> dict:
    # Fetch access token
    token = await _fetch_access_token(session)
    # Construct the header.
    header = {'Authorization': 'Bearer {}'.format(token['access_token'])}
    return header

def prepare_fetch_hourlies_query(station_id):
    """ Prepare url and params to fetch hourly actuals from the BC FireWeather Phase 1 API.
    """
    base_url = config.get('BC_FIRE_WEATHER_BASE_URL')
    # By default we're concerned with the last 5 days only.
    now = _get_now()
    five_days_ago = now - timedelta(days=5)
    LOGGER.debug('requesting hourly actuals data from %s to %s for station %s', five_days_ago, now, station_id)
    # Prepare query params and query:
    start_time_stamp = math.floor(five_days_ago.timestamp()*1000)
    end_time_stamp = math.floor(now.timestamp()*1000)
    params = {
        'Start_Date': start_time_stamp,
        'End_Date': end_time_stamp, 
        'Station_Code': station_id,
        'Format': 'CSV',
        'cboFilters': 0,
        'rdoReport': 'OSBH'
      }
    endpoint = ('Scripts/Public/Common/Results_Report.asp')
    url = '{base_url}{endpoint}'.format(
        base_url=base_url,
        endpoint=endpoint)
    return url, params

def _get_stations_local() -> List[WeatherStation]:
    """ Get list of stations from local json files.
    """
    LOGGER.info('Using pre-generated json to retrieve station list')
    with open(weather_stations_file_path) as weather_stations_file:
        json_data = json.load(weather_stations_file)
        return json_data['weather_stations']

async def fetch_hourlies(
        session: ClientSession,
        station_id: int,
        headers: dict):
    """ Fetch hourly weather readings for a given station.
    """
    url, params = prepare_fetch_hourlies_query(station_id)
    # Get hourlies
    async with session.get(url, params=params, headers=headers) as response:
        await response
        BC_FIRE_WEATHER_CSV_URL = re.findall(r"\/fire_weather\/csv\/.+\.csv", response)   # pylint: disable=invalid-name
        LOGGER.info('CSV available at %s', BC_FIRE_WEATHER_CSV_URL)
        return BC_FIRE_WEATHER_CSV_URL

async def get_csv(
        session: ClientSession,
        headers: dict,
        csv_url: str):
    """ Fetch CSV of hourly actual weather for a station.
    """
    url = config.get('BC_FIRE_WEATHER_BASE_URL') + csv_url
    async with session.get(url, headers=headers) as response:
        await response
        return


async def get_hourly_actuals():
    """ For each station, send POST request to BC FireWeather API to generate a CSV,
    then send GET request to retrieve the CSV,
    then parse the CSV and store in DB.
    """
    conn = TCPConnector()
    async with ClientSession(connector=conn) as session:
        # Get the authentication header
        header = await _get_auth_header(session)

        # Iterate through station data.
        iterator = _get_stations_local()
        for station in iterator:
            # Submit the POST request to query hourly actuals for the station
            csv_url = fetch_hourlies(session, station['code'], header)
            # Use the returned URL to fetch the CSV data for the station
            csv_data = get_csv(session, header, csv_url)
            # Parse the CSV data
            parse_csv(csv_data, station['code'])

def parse_csv(csv_data: str, station_id: int):
    """ Given a CSV of hourly actual weather data for a station, load the CSV into a 
    pandas dataframe, then insert the dataframe into the DB. (This 2-step process is
    the neatest way to write CSVs into a DB.)
    """
    data_df = pd.read(csv_data)
    # replace first column (station name) in df with station_id
    data_df['display_name'].replace(station_id, inplace=True)
    # TODO fix this up
    data_df.to_sql('hourly_station_actuals', con=engine, index=True, index_label='', if_exists='replace')


def _get_now():
    """ Helper function to get the current time (easy function to mock out in testing) """
    return datetime.now(tz=pytz.utc)
