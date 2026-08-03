Feature: Transaction tags
  As a consumer application (firefly-bills-analyzer)
  I want each transaction split to carry the tags the user applied to it
  So that I can let the user override a classification I derived from the
  category, on individual transactions, without them having to restructure
  their categories to express an exception

  Scenario: Tags are returned on a withdrawal
    Given a withdrawal split carrying two tags in the API response
    When get_withdrawal_transactions is called
    Then the returned record's tags holds both tag strings, in the order the API returned them

  Scenario: Tags are returned on a deposit
    Given a deposit split carrying one tag in the API response
    When get_deposit_transactions is called
    Then the returned record's tags holds that tag

  Scenario: An absent tags field becomes an empty list
    Given a split whose API response contains no tags key
    When either fetch method is called
    Then the returned record's tags is an empty list and not None

  Scenario: A null tags field becomes an empty list
    Given a split whose API response contains a null tags value
    When either fetch method is called
    Then the returned record's tags is an empty list

  Scenario: Tag strings are preserved verbatim
    Given a split tagged with surrounding whitespace and mixed case
    When either fetch method is called
    Then the returned tag string is byte-identical to the API's value

  Scenario: Each split carries its own tags
    Given a multi-split transaction whose two splits carry different tags
    When either fetch method is called
    Then each returned record carries the tags of its own split

  Scenario: Existing fields are unchanged
    Given the completed implementation
    When the existing get_withdrawal_transactions and get_deposit_transactions tests are run
    Then they pass, and no field other than tags changed value
