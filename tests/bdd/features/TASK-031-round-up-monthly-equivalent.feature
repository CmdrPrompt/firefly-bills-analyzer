Feature: Round the monthly equivalent up to the nearest öre
  As a user planning cash flow across the full year
  I want each pattern's monthly equivalent rounded to whole öre in a direction that never understates the cost
  So that the exported figures are readable currency amounts and summing them never quietly undercounts my monthly spend

  Scenario: A monthly equivalent with a non-terminating fraction is rounded up to the nearest öre
    Given a quarterly pattern with a mean amount of 100.0
    When the pattern is built
    Then its monthly_equivalent is 33.34

  Scenario: A monthly equivalent already exact to two decimals is unchanged
    Given a monthly pattern with a mean amount of 42.50
    When the pattern is built
    Then its monthly_equivalent is 42.5

  Scenario: Irregular pattern records no monthly equivalent
    Given a payee group whose billing events recur at a median interval outside every range in `_FREQUENCY_RANGES`
    When the pattern is built
    Then its monthly_equivalent is None
