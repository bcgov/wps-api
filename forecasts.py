""" This module contain logic to retrieve predicted weather data.
"""
from os import getenv
from datetime import datetime, timedelta
import asyncio
import json
import logging
from io import StringIO
from typing import List
import pandas
from aiohttp import ClientSession
from schemas import WeatherForecast, WeatherStation, WeatherForecastValues

LOGGER = logging.getLogger(__name__)


class StationNotFoundException(Exception):
    """ Custom exception for when a station cannot be found """


def fetch_station_by_code(station_code: int) -> WeatherStation:
    """ Return a station matching the specified code """
    # NOTE: This will change to use the WildeFire API.
    with open('data/weather_stations.json') as file_pointer:
        stations = json.load(file_pointer)
        for station in stations['weather_stations']:
            if int(station['code']) == station_code:
                return WeatherStation(**station)
        raise StationNotFoundException()


def get_key_map():
    """ Key value map from spotwx to out structure. """
    return {
        'DATETIME': 'datetime',
        # Temperature, 2 meters above ground, units = Celsius.
        'TMP': 'temperature',
        # Dew Point, 2 meters above ground, units = Celsius.
        'DP': 'dew_point',
        # Relative Humidity, 2 meters above ground, units = Percent.
        'RH': 'relative_humidity',
        # Wind Speed, 10 meters above ground, units = km/h.
        'WSPD': 'wind_speed',
        # Wind Direction, 10 meters above ground, units = degrees true.
        'WDIR': 'wind_direction',
        'PRECIP_ttl': 'total_precipitation',
        # Accumulated rain, surface, units = millimeters.
        'RQP': 'accumulated_rain',
        # Accumulated snow water equivalent, surface, units = millimeters
        # (NOTE: Also equals approximate snowfall in centimeters. ie. 1mm of
        # snow water equivalent = 1cm of fresh snow, on average for a fresh snowfall).
        'SQP': 'accumulated_snow',
        # Accumulated freezing rain, surface, units = millimeters.
        'FQP': 'accumulated_freezing_rain',
        # Accumulated ice pellets, surface, units = millimeters.
        'IQP': 'accumulated_ice_pellets',
        # Cloud coverage, total in all levels, units = Percent of sky covered.
        'CLOUD': 'cloud_cover',
        # Sea Level Pressure, units = millibars.
        'SLP': 'sea_level_pressure',
        'WSPD_40M': 'wind_speed_40m',
        'WDIR_40M': 'wind_direction_40m',
        "WDIR_80M": "wind_direction_80m",
        'WSPD_80M': 'wind_speed_80m',
        "WSPD_120M": "wind_speed_120m",
        "WDIR_120M": "wind_direction_120m",
        "WSPD_925MB": "wind_speed_925mb",
        "WDIR_925MB": "wind_direction_925mb",
        "WSPD_850MB": "wind_speed_850mb",
        "WDIR_850MB": "wind_direction_850m"
    }


async def fetch_forecast(session: ClientSession, station_code: int) -> WeatherForecast:
    """ Return the forecast for a weather station from spotwx.
    """
    # We need the station coordinates, spotwx doesn't know about station id's.
    station = fetch_station_by_code(station_code)

    url = '{base_url}?key={key}&model={model}&lat={lat}&lon={long}'.format(
        lat=station.lat, long=station.long, model='gdps', key=getenv('SPOTWX_API_KEY'),
        base_url=getenv('SPOTWX_BASE_URI'))

    LOGGER.debug('getting response from spotwx for %d...', station_code)
    async with session.get(url) as response:
        csv_data = await response.text()
    LOGGER.debug('retreived response from spotwx for %d, csv data: %s...',
                 station_code, csv_data[:20])

    # Data from spotwx comes back as csv :(
    # NOTE: There is scope for reading data with csvreader as it comes in to improve speed.
    data = pandas.read_csv(StringIO(csv_data))

    # Set the column types correctly.
    data['DATETIME'] = pandas.to_datetime(data['DATETIME'])
    for column in data:
        if column != 'DATETIME':
            data = data.astype({column: float})

    # We're only interested in local noon values.
    # 1. The global model runs on 3 hour intervals - for PST, there is no noon value.
    # 2. 20 hours UTC is 12 hours (noon) PST (pacific standard time).
    # 3. All coordinates are in PST.

    # Insert the missing noon values, starting at the start date
    start_date = data['DATETIME'][0]
    # All stations use a UTC offset of -8 hours. This gives us a noon time for PST.
    station_offset = -8
    # Calculate noon in UTC.
    utc_noon = 12+abs(station_offset)
    # Reformat to propper date object.
    start_date = datetime(
        year=start_date.year, month=start_date.month, day=start_date.day, hour=utc_noon)
    # Iterate for 10 days.
    for day in range(10):
        data = data.append(
            {'DATETIME': start_date + timedelta(hours=day*24)}, ignore_index=True)
    # Fix the ordering.
    data = data.sort_values(by=['DATETIME'])
    # Set the index to use the date column, for appropriate interpolation.
    data = data.set_index('DATETIME', drop=False)
    # Interpolate using time. (All the null values from our data insert will now be populated)
    data = data.interpolate(method='time')
    # Filter to noon values only.
    data = data.at_time('{}:00:00'.format(utc_noon))
    # Rename all columns using our key map.
    data = data.rename(columns=get_key_map())
    # Create forecast object to return.
    forecast = WeatherForecast(station=station)
    for row in data.to_dict(orient='records'):
        forecast.values.append(WeatherForecastValues(**row))
    return forecast


async def fetch_forecast_with_semaphore(
        semaphore: asyncio.Semaphore,
        station_code: int, session: ClientSession) -> asyncio.Future:
    """ Fetch a forecast for a station using a semaphor.
    """
    async with semaphore:
        return await fetch_forecast(session, station_code)


async def fetch_forecasts(station_codes: List[int]) -> asyncio.Future:
    """ Fetch forecasts for all stations concurrently.
    """
    # Create a list containing all the tasks to run in parallel.
    tasks = []
    # Limit the number of concurrent tasks that can be run to 10, using a semaphore.
    # NOTE: Wouldn't using TCPConnector with a pool limit give us the same as using the semaphore?
    semaphore = asyncio.Semaphore(10)

    async with ClientSession() as session:
        # Line up tasks
        for station_code in station_codes:
            task = asyncio.create_task(
                fetch_forecast_with_semaphore(semaphore, station_code, session))
            tasks.append(task)
        # Run the tasks concurrently, waiting for them all to complete.
        return await asyncio.gather(*tasks)