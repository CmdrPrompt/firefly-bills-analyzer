# TASK-025: Fetch deposits for configured income accounts (UC12)
Feature: Fetch deposits for configured income accounts
  As a user who wants a cost split based on what I actually earn
  I want the application to read the deposits landing on my salary account
  So that the income figure comes from my transaction history rather than a config value

  @AC-1
  Scenario: No income account configured means no deposit fetch
    Given INCOME_ACCOUNTS is empty
    When the analysis runs
    Then no deposit request is made to the API
    And no client is constructed for deposits
    And the run's behavior is identical to today's

  @AC-2
  Scenario: Deposits are fetched for the configured window
    Given INCOME_ACCOUNTS names one account
    And LOOKBACK_MONTHS is 24
    When the analysis runs
    Then get_deposit_transactions is called with the same start and end dates as fetch_transactions used in that run

  @AC-3
  Scenario: Deposits to other accounts are discarded
    Given deposits landing on both a configured income account and an unconfigured account
    When fetch_deposits returns
    Then only records whose destination_name matches an income account are present in the result

  @AC-4
  Scenario: Deposits never reach the withdrawal pipeline
    Given a run with income accounts configured
    When the analysis completes
    Then no deposit record is passed to payee grouping, category filtering, account filtering, payee filtering, or bill creation

  @AC-5
  Scenario: Deposits are cached under their own key
    Given a completed run with income accounts configured
    When the cache directory is inspected
    Then a deposits cache entry exists distinct from the transactions entry
    And a second run within CACHE_TTL_TRANSACTIONS makes no deposit request

  @AC-6
  Scenario: A cached window mismatch forces a refetch
    Given a cached deposit entry whose window differs from the current run's
    When the analysis runs
    Then the deposits are fetched again rather than read from cache

  @AC-7
  Scenario: An unreachable instance is reported, not crashed
    Given the deposit fetch raises FireflyConnectionError
    When the analysis runs
    Then the error is reported per NFR-04 with no stack trace
