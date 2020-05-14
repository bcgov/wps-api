""" Functional testing for /forecasts/ endpoint.
"""
import logging
from datetime import datetime
from fastapi.testclient import TestClient
import numpy
from main import APP


LOGGER = logging.getLogger(__name__)
client = TestClient(APP)
headers = {'Authorization': "Bearer token"}


def test_get_forecasts_with_invalid_token():
    """test /forecasts/ without valid token"""
    r = client.post('/forecasts/', headers=headers)
    assert r.status_code == 401
    error_msg = 'Could not validate the credential (Not enough segments)'
    assert r.json()['detail'] == error_msg


def test_get_forecasts(mock_jwt_decode, mock_client_session_get):
    """test /forecasts/ endpoint with valid token"""

    # request without correct body
    r = client.post('/forecasts/', headers=headers)
    assert r.status_code == 422

    # request with correct body
    r2 = client.post('/forecasts/', headers=headers,
                     json={"stations": [
                         331,
                         328
                     ]})
    assert r2.status_code == 200
    r2_json = r2.json()

    # --- test number of forecast ---
    assert len(r2_json['forecasts']) == 2

    # --- test 10 day forecast ---
    assert len(r2_json['forecasts'][0]['values']) == 10

    # --- test noon values only ---
    for forecast in r2_json['forecasts']:
        for values in forecast['values']:
            timestamp = datetime.fromisoformat(values['datetime'])
            assert timestamp.hour == 20

    # --- test temperature values only ---
    x_p = [datetime.fromisoformat('2020-05-04T18:00:00').timestamp(),
           datetime.fromisoformat('2020-05-04T21:00:00').timestamp()]
    f_p = [8.7, 12.1]  # temperatures matching csv file:
    expected_temperature = numpy.interp(datetime.fromisoformat(
        '2020-05-04T20:00:00').timestamp(), x_p, f_p)  # calculate interpolated temperature
    assert r2_json['forecasts'][0]['values'][0]['temperature'] == expected_temperature
