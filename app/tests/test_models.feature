Feature: /models/

    Scenario: Get models from spotwx
        Given I request weather models for stations: <codes>
        Then the response status code is <status>
        And there are <num_models> from two stations
        And there are 3 hourly model with 10 days of interpolated noon values for each station
        And model values should be interpolated

        Examples:
            | codes      | status | num_models |
            | [331, 328] | 200    | 2          |
            | [331]      | 200    | 1          |
