""" Unit tests for app/fireweather_bot.py """

import pytest
from alchemy_mock.mocking import UnifiedAlchemyMagicMock
import fireweather_bot

@pytest.fixture()
def mock_request_noon_forecast(monkeypatch):
    """ fixture for """

    monkeypatch.setattr()

def test_main():
    """ Run main method to test """
    # mock writing the data to the database
    session = UnifiedAlchemyMagicMock()
    fireweather_bot.main()
