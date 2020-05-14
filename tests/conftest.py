""" Global fixtures """

import logging
import json
import jwt
import pytest
from aiohttp import ClientSession
import config
from tests.common import FixtureResolver

LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """ Automatically mock environment variable """

    monkeypatch.setenv("SPOTWX_API_KEY", "something")
    monkeypatch.setenv("USE_WFWX", 'False')
    monkeypatch.setenv("WFWX_USER", "user")
    monkeypatch.setenv("WFWX_SECRET", "secret")
    monkeypatch.setenv("WFWX_AUTH_URL", "http://localhost/v1/oauth/token")
    monkeypatch.setenv("WFWX_BASE_URL", "http://localhost/page")
    monkeypatch.setenv("WFWX_MAX_PAGE_SIZE", "1000")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_KEY", "public_key")


@pytest.fixture()
def mock_env_with_use_wfwx(monkeypatch):
    """ Set environment variable USE_WFWX to 'True' """

    monkeypatch.setenv("USE_WFWX", 'True')


class MockJWTDecode:
    """ Mock pyjwt module """

    @staticmethod
    def decode():
        return {}


@pytest.fixture
def mock_jwt_decode(monkeypatch):
    """ Mock pyjwt's decode method """

    def mock(*args, **kwargs):
        return MockJWTDecode()

    monkeypatch.setattr(jwt, "decode", mock)


class MockResponse:
    """ Stubbed response object.
    """

    def __init__(self, text_response=None, json_response=None):
        """ Initialize client response """
        self.text_response = text_response
        self.json_response = json_response

    async def text(self) -> str:
        """ Return text response """
        return self.text_response

    async def json(self) -> dict:
        """ Return json response """
        return self.json_response


class MockClientSession:
    """ Stubbed asyncronous context manager. """

    def __init__(self, url, params=None):
        """ Remember the url so that we can change our response depending on the request. """
        self.url = url
        self.params = params

    async def __aenter__(self):
        """ Enter context - return the appropriate response object depending on the url """
        resolver = FixtureResolver(self.url, self.params)

        if config.get('SPOTWX_BASE_URI') in self.url:
            with open('tests/spotwx_response_sample.csv', mode='r') as spotwx:
                data = spotwx.read()
                return MockResponse(text_response=data)
        else:
            return MockResponse(json_response=resolver.get_fixture_json())

    # pylint: disable=invalid-name

    async def __aexit__(self, exc_type, exc, tb):
        """ Exit context """


@pytest.fixture
def mock_client_session_get(monkeypatch):
    """ mock ClientSession's get method """

    def mock(obj, url, params=None, *args, **kwargs):
        return MockClientSession(url=url, params=params)

    monkeypatch.setattr(ClientSession, 'get', mock)
