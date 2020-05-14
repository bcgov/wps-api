""" Functional testing for API - stations using wf1 """

from fastapi.testclient import TestClient
from main import APP

client = TestClient(APP)


def test_get_stations(mock_env_with_use_wfwx, mock_client_session_get):
    r = client.get('/stations/')
    assert len(r.json()['weather_stations']) == 16

    actual_station = r.json()['weather_stations'][0]
    assert actual_station == {'code': 67, 'name': 'HAIG CAMP',
                                          'lat': 49.3806, 'long': -121.525967}
