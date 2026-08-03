Feature: Fetch deposit transactions
  As a consumer application (firefly-bills-analyzer)
  I want deposit transactions in a date range with the same pagination and
  split flattening the withdrawal side already gets
  So that I can detect a recurring salary payment on an asset account instead
  of asking the user to type their net income into a configuration file

  Scenario: Deposits are requested with the deposit type filter
    Given a valid date range
    When get_deposit_transactions is called
    Then the request is GET /api/v1/transactions with query parameters type=deposit, start, end, and page=1

  Scenario: All pages are followed
    Given an API response reporting total_pages of 3
    When get_deposit_transactions is called
    Then pages 1, 2, and 3 are requested and the returned list contains the splits from all three

  Scenario: Multi-split deposits are flattened
    Given a deposit transaction object with two splits under attributes.transactions
    When get_deposit_transactions is called
    Then the returned list contains one TransactionRead per split

  Scenario: Account roles follow the API for a deposit
    Given a deposit split whose source_name is a revenue account and whose destination_name is an asset account
    When get_deposit_transactions is called
    Then the returned TransactionRead carries that revenue account in source_name and that asset account in destination_name

  Scenario: Absent fields default to None
    Given a deposit split with no category_name, no source_name, and no source_id in the API response
    When get_deposit_transactions is called
    Then those fields are None on the returned TransactionRead

  Scenario: Progress callback is invoked per page
    Given an API response reporting total_pages of 2
    When get_deposit_transactions is called with an on_page callback
    Then callback is invoked as (1, 2) and (2, 2), in that order

  Scenario: A callback exception stops fetching
    Given a callback that raises on the first page
    When get_deposit_transactions is called with an on_page callback
    Then the exception propagates to the caller and no further page is requested

  Scenario: Transfers are not returned
    Given an account with both deposits and transfers in the date range
    When get_deposit_transactions is called
    Then the request carries type=deposit and no transfer record appears in the result

  Scenario: Connection failure is reported
    Given the API responds with a non-2xx status
    When get_deposit_transactions is called
    Then FireflyConnectionError is raised
