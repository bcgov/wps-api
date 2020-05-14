""" BDD tests for API /hourlies. """
import logging
from unittest.mock import patch
from pytest_bdd import scenario, given, then
from starlette.testclient import TestClient
from main import APP
import tests.common

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class ResponseAsyncContextManager(tests.common.ResponseAsyncContextManagerAutoFixture):
    """ Stubbed asyncronous context manager.
    """

    def _clean_params(self):
        """ Remove troublesome parameters.
        """
        # We ignore the timestamps.
        ignore = ['startTimestamp', 'endTimestamp']
        for item in ignore:
            if item in self.params:
                del self.params[item]


@scenario('test_get_hourlies.feature', 'Get hourlies',
          example_converters=dict(codes=str, status=int, num_groups=int, num_readings_per_group=str))
def test_hourlies():
    """ BDD Scenario. """


@given('I request hourlies for stations: <codes>')
@patch('wildfire_one.ClientSession.get')
def response(mock_client_session_get, codes):
    """ Make /hourlies/ request using mocked out ClientSession.
    """
    # Extract the list of station codes.
    # NOTE: should be using a converter
    # pylint: disable=eval-used
    stations = eval(codes)

    # Attach a side effect to the mocked out ClientSession.
    # pylint: disable=unused-argument
    def get_side_effect(url, params=None, **args):
        return ResponseAsyncContextManager(url, params)
    mock_client_session_get.side_effect = get_side_effect

    # Create API client and get the reppnse.
    client = TestClient(APP)
    return client.post('/hourlies/', headers={'Content-Type': 'application/json'},
                       json={"stations": stations})


# pylint: disable=redefined-outer-name
@then('the response status code is <status>')
def assert_status_code(response, status):
    """ Assert that we recieve the expected status code """
    assert response.status_code == status


@then('there are <num_groups> groups of hourlies')
def assert_number_of_hourlies_groups(response, num_groups):
    """ Assert that we recieve the expected number of hourly groups """
    assert len(response.json()['hourlies']) == num_groups


@then('there are <num_readings_per_group> readings per group')
def assert_number_of_hourlies_per_group(response, num_readings_per_group):
    """ Assert that we receive the expected number of hourlies per groups """
    # pylint: disable=eval-used
    for index, item in enumerate(eval(num_readings_per_group)):
        assert len(response.json()['hourlies']
                   [index]['weather_readings']) == item
