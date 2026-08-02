# Feature: Normalized monthly equivalent per billing pattern
Feature: Normalized monthly equivalent per pattern
  As a user planning cash flow across the full year
  I want each identified pattern to carry a per-month figure alongside its frequency and mean amount
  So that I can sum a set of patterns billed at different cadences without doing the division by hand in a spreadsheet after every export

  Scenario: Monthly pattern reports its mean amount unchanged
    Given a payee group whose billing events recur at a median interval inside the monthly range (25-35 days)
    When `identify_recurring()` builds the pattern
    Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 1

  Scenario: Quarterly pattern is divided by 3
    Given a payee group whose billing events recur at a median interval inside the quarterly range (80-100 days)
    When `identify_recurring()` builds the pattern
    Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 3

  Scenario: Half-yearly pattern is divided by 6
    Given a payee group whose billing events recur at a median interval inside the half-yearly range (160-200 days)
    When `identify_recurring()` builds the pattern
    Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 6

  Scenario: Yearly pattern is divided by 12
    Given a payee group whose billing events recur at a median interval inside the yearly range (340-390 days)
    When `identify_recurring()` builds the pattern
    Then the pattern's `monthly_equivalent` equals its `amount_mean` divided by 12

  Scenario: Irregular pattern records no monthly equivalent
    Given a payee group whose billing events recur at a median interval outside every range in `_FREQUENCY_RANGES`
    When `identify_recurring()` builds the pattern
    Then the pattern's `frequency` is `irregular` and its `monthly_equivalent` is `None`

  Scenario: A single billing event yields no monthly equivalent
    Given a payee group that produces exactly one billing event, so no interval can be computed and `median_interval_days` is 0.0
    When `identify_recurring()` builds the pattern
    Then the pattern's `frequency` is `irregular` and its `monthly_equivalent` is `None`

  Scenario: The monthly equivalent reaches the CSV export
    Given a list of patterns containing one quarterly pattern and one irregular pattern
    When `exporter.export(patterns, "csv", path)` writes the file
    Then the header row contains a `monthly_equivalent` column, the quarterly row carries its computed value, and the irregular row carries an empty cell

  Scenario: The monthly equivalent reaches the JSON export
    Given the same list of patterns
    When `exporter.export(patterns, "json", path)` writes the file
    Then each object carries a `monthly_equivalent` key, `null` for the irregular pattern
