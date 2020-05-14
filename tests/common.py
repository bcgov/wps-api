""" Code common to tests
"""
import logging
from abc import abstractmethod, ABC
import os
import json
from urllib.parse import urlencode


LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class ClientResponse:
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


# DEPRECATED! Stop using this.
class ResponseAsyncContextManagerBase:
    """ Stubbed asyncronous context manager.
    """

    def __init__(self, url, params=None):
        """ Remember the url so that we can change our response depending on the request.
        """
        self.url = url
        self.params = params

    async def __aenter__(self):
        """ Enter context - return the appropriate response object depending on the url
        """
        if 'token' in self.url:
            return ClientResponse(json_response={'access_token': 'token'})
        raise Exception('unexpected url: {}'.format(self.url))

    # pylint: disable=invalid-name
    async def __aexit__(self, exc_type, exc, tb):
        """ Exit context
        """


class FixtureResolver:
    def __init__(self, url, params=None):
        self.url = url
        self.params = params
        self._ignore_params = ['disableDeveloperFilter', 'grant_type', 'scope']

    def _clean_params(self):
        """ Remove troublesome parameters.
        """
        # We ignore all these params
        for item in self._ignore_params:
            if item in self.params:
                del self.params[item]

    def _get_fixture_path(self):
        """ Return the filename of the fixture file.
        """
        # We only care from v1 onwards...
        url = self.url[self.url.find('v1'):]
        if self.params:
            # There may be some parameters we choose to ignore.
            self._clean_params()
            # Build up the url
            url = '{}?{}'.format(url, urlencode(self.params))
        # Join the url with the fixture location.
        filename = os.path.join('tests/fixtures/', url)
        # Slap .json on the end.
        return filename + '.json'

    def get_fixture_json(self):
        # TODO: right herer dude! So - rather than assume it's json, look at the fixture and see if it's text or json
        fixture = self._get_fixture_path()
        if os.path.exists(fixture):
            with open(fixture, 'r') as fixture_file:
                return json.load(fixture_file)
        else:
            raise Exception('fixture not found: {}'.format(fixture))


class ResponseAsyncContextManagerAutoFixture:
    """ Stubbed asyncronous context manager that pulls in fixtures automatically. """

    def __init__(self, url, params=None):
        """ Remember the url so that we can change our response depending on the request.
        """
        self._fixture_resolver = FixtureResolver(url, params)

    async def __aenter__(self):
        """ Enter context """
        fixture_json = self._fixture_resolver.get_fixture_json()
        return ClientResponse(json_response=fixture_json)

    # pylint: disable=invalid-name
    async def __aexit__(self, exc_type, exc, tb):
        """ Exit context
        """
