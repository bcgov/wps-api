""" Functional testing for authentication """
from pytest_bdd import scenario, given, then
from fastapi.testclient import TestClient
import app.main


# pylint: disable=unused-argument, redefined-outer-name
@scenario('test_auth.feature', 'Handling unauthenticated users',
          example_converters=dict(token=str, status=int, message=str, endpoint=str))
def test_auth_1st_scenario():
    """ BDD Scenario #1. """


@given("I am an unauthenticated user <token> when I access a protected <endpoint>")
def response(token: str, endpoint: str):
    """ Make POST {endpoint} request which is protected """
    client = TestClient(app.main.app)
    return client.post(endpoint, headers={'Authorization': token})

@then("I will get an error with <status> code")
def status_code(response, status: int):
    """ Assert that we receive the expected status code """
    assert response.status_code == status


@then("I will see an error <message>")
def error_message(response, message: str):
    """ Assert that we receive the expected message """
    assert response.json()['detail'] == message


@scenario("test_auth.feature", "Verifying authenticated users", example_converters=dict(status=int))
def test_auth_2nd_scenario():
    """ BDD Scenario #2. """


@given("I am an authenticated user when I access a protected <endpoint>")
def response_2(mock_jwt_decode, endpoint: str):
    """ Make POST {endpoint} request which is protected """
    client = TestClient(app.main.app)
    return client.post(
        endpoint, headers={'Authorization': 'Bearer token'}, json={"stations": []})


@then("I shouldn't get an unauthorized error <status> code")
def status_code_2(response_2, status: int):
    """ Assert that we receive the expected status code """
    assert response_2.status_code == status
