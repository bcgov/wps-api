""" Unit tests for app/env_canada.py """

import os
import logging
import datetime
import pytest
import requests
from alchemy_mock.mocking import UnifiedAlchemyMagicMock
from alchemy_mock.compat import mock
from app.models import env_canada
from app.db.models import PredictionModel, ProcessedModelRunUrl
import app.db.database
# pylint: disable=unused-argument, redefined-outer-name


logger = logging.getLogger(__name__)


class MockResponse:
    """ Mocked out request.Response object """

    def __init__(self, status_code, content=None):
        self.status_code = status_code
        self.content = content


@pytest.fixture()
def mock_utcnow(monkeypatch):
    """ Mocked out utcnow, to allow for deterministic tests """
    def mock_get_utcnow(*args):
        return datetime.datetime(year=2021, month=2, day=3, hour=0)
    monkeypatch.setattr(env_canada, 'get_utcnow', mock_get_utcnow)


@pytest.fixture()
def mock_session(monkeypatch):
    """ Mocked out sqlalchemy session object """
    def mock_get_session(*args):
        url = ('https://dd.weather.gc.ca/model_gem_global/15km/grib2/lat_lon/00/000/'
               'CMC_glb_TMP_TGL_2_latlon.15x.15_2021020300_P000.grib2')
        return UnifiedAlchemyMagicMock(data=[
            (
                [mock.call.query(PredictionModel),
                 mock.call.filter(PredictionModel.abbreviation == 'GDPS',
                                  PredictionModel.projection == 'latlon.15x.15')],
                [PredictionModel(abbreviation='GDPS',
                                 projection='latlon.15x.15')],
            ),
            (
                [mock.call.query(ProcessedModelRunUrl),
                 mock.call.filter(ProcessedModelRunUrl.url == url)],
                [ProcessedModelRunUrl()]

            )
        ])
    monkeypatch.setattr(app.db.database, 'get_session', mock_get_session)


@pytest.fixture()
def mock_download(monkeypatch):
    """ fixture for env_canada.download """
    def mock_requests_get(*args, **kwargs):
        """ mock env_canada download method """
        dirname = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(
            dirname, 'CMC_glb_RH_TGL_2_latlon.15x.15_2020071300_P000.grib2')
        with open(filename, 'rb') as file:
            content = file.read()
        return MockResponse(status_code=200, content=content)
    monkeypatch.setattr(requests, 'get', mock_requests_get)


@pytest.fixture()
def mock_download_fail(monkeypatch):
    """ fixture for env_canada.download """
    def mock_requests_get(*args, **kwargs):
        """ mock env_canada download method """
        return MockResponse(status_code=400)
    monkeypatch.setattr(requests, 'get', mock_requests_get)


def test_get_download_urls():
    """ test to see if get_download_urls methods give the correct number of urls """
    total_num_of_urls = len(['00', '12']) * 81 * len(['TMP_TGL_2', 'RH_TGL_2'])
    assert len(list(env_canada.get_download_urls())) == total_num_of_urls


def test_main(mock_download, mock_session, mock_utcnow):
    """ run main method to see if it runs successfully. """
    # All files, except one, are marked as already having been downloaded, so we expect one file to
    # be processed.
    assert env_canada.main() == 1
