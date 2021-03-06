""" This module contains pydandict schemas for the API.
"""
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel


class Season(BaseModel):
    """ A fire season consists of a start date (month and day) and an end date (month and day). """
    start_month: int
    start_day: int
    end_month: int
    end_day: int


class WeatherStation(BaseModel):
    """ A fire weather station has a code, name and geographical coordinate. """
    code: int
    name: str
    lat: float
    long: float
    ecodivision_name: str = None
    core_season: Season


class YearRange(BaseModel):
    """ A request for data spans a range of years. """
    start: int
    end: int


class PercentileRequest(BaseModel):
    """ A request for some quantile for a given set of stations over a specified year range. """
    stations: List[int]
    percentile: int
    year_range: YearRange


class StationSummary(BaseModel):
    """ The summary of daily weather data for a given station. """
    ffmc: float = None
    isi: float = None
    bui: float = None
    years: List[int]
    station: WeatherStation


class MeanValues(BaseModel):
    """ The mean percentile values for set of stations. """
    ffmc: float = None
    isi: float = None
    bui: float = None


class CalculatedResponse(BaseModel):
    """ The combined response for a set of stations. """
    stations: Dict[int, StationSummary] = {}
    mean_values: MeanValues = None
    year_range: YearRange
    percentile: int


class WeatherStationsResponse(BaseModel):
    """ List of fire weather stations. """
    weather_stations: List[WeatherStation]


class WeatherReading(BaseModel):
    """ Weather reading for a particular point in time """
    datetime: datetime
    temperature: float = None
    relative_humidity: float = None
    wind_speed: float = None
    wind_direction: float = None
    barometric_pressure: float = None
    precipitation: float = None
    ffmc: float = None
    isi: float = None
    fwi: float = None


class WeatherStationHourlyReadings(BaseModel):
    """ The weather readings for a particular station """
    values: List[WeatherReading]
    station: WeatherStation


class WeatherPredictionModel(BaseModel):
    """ The full name & acronym for a weather prediction model """
    name: str
    abbrev: str


class WeatherModelPredictionValues(BaseModel):
    """ The predicted weather values. """
    datetime: datetime
    temperature: float = None
    dew_point: float = None
    relative_humidity: float = None
    wind_speed: float = None
    wind_direction: float = None
    total_precipitation: float = None
    accumulated_rain: float = None
    accumulated_snow: float = None
    accumulated_freezing_rain: float = None
    accumulated_ice_pellets: float = None
    cloud_cover: float = None
    sea_level_pressure: float = None
    wind_speed_40m: float = None
    wind_direction_40m: float = None
    wind_direction_80m: float = None
    wind_speed_120m: float = None
    wind_direction_120m: float = None
    wind_speed_925mb: float = None
    wind_direction_925mb: float = None
    wind_speed_850mb: float = None
    wind_direction_850mb: float = None


class WeatherModelRun(BaseModel):
    """ Detail about the model run """
    datetime: datetime
    name: str
    abbreviation: str
    projection: str


class WeatherModelPrediction(BaseModel):
    """ Weather model prediction for a particular weather station. """
    station: WeatherStation
    model_run: WeatherModelRun = None
    values: List[WeatherModelPredictionValues] = []


class WeatherModelPredictionResponse(BaseModel):
    """ Response containg a number of weather predictions. """
    predictions: List[WeatherModelPrediction]


class WeatherStationHourlyReadingsResponse(BaseModel):
    """ Response containing a number of hourly readings. """
    hourlies: List[WeatherStationHourlyReadings]


class StationCodeList(BaseModel):
    """ List of station codes. """
    stations: List[int]


class Ecodivision(BaseModel):
    """ Name and core fire season of BC Ecodivision. """
    name: str
    core_season: Season


class NoonForecastValue(BaseModel):
    """ Data structure for a noon forecast retrieved from BC FireWeather Phase 1 """
    datetime: datetime
    temp_valid: bool
    temperature: int
    rh_valid: bool
    relative_humidity: int
    wdir_valid: bool
    wind_direction: int = None
    wspeed_valid: bool
    wind_speed: float
    precip_valid: bool
    total_precipitation: float
    gc: float = None
    ffmc: float = None
    dmc: float = None
    dc: float = None
    isi: float = None
    bui: float = None
    fwi: float = None
    danger_rating: int = None
    created_at: datetime


class NoonForecast(BaseModel):
    """ Data structure for returning forecasts for a particular station """
    station_code: int
    values: List[NoonForecastValue]


class NoonForecastResponse(BaseModel):
    """ Response containg a number of noon forecasts. """
    noon_forecasts: List[NoonForecast]


class WeatherModelPredictionSummaryValues(BaseModel):
    """ Summary of model prediction values. """
    datetime: datetime
    tmp_tgl_2_5th: float
    tmp_tgl_2_90th: float
    tmp_tgl_2_median: float
    rh_tgl_2_5th: float
    rh_tgl_2_90th: float
    rh_tgl_2_median: float


class WeatherModelPredictionSummary(BaseModel):
    """ Summary of weather predictions for a given model.
    Detail: For the global model, we end up with 20 different predictions for every three hours of any given
    day, this represents a summary of that data. """
    station: WeatherStation
    model: WeatherPredictionModel
    values: List[WeatherModelPredictionSummaryValues] = []


class WeatherModelPredictionSummaryResponse(BaseModel):
    """ Response containing prediction summaries for a given weather model."""
    summaries: List[WeatherModelPredictionSummary]
