# TASK-027: Export and display income sources (UC12)
Feature: Export and display income sources
  As a user, I want the detected income written to a file next to the
  recurring payment export, so that a downstream tool can consume both
  without me copying numbers between them, and so that an account where
  detection failed is visible in the file rather than merely absent from it.

  @AC-1
  Scenario: Income is exported to its own file
    Given a run with one detected income source and EXPORT_FORMAT=csv
    When the run completes
    Then two files are written, the pattern export and an income export
    And the income file contains one row with status "ok"

  @AC-2
  Scenario: JSON format is honored
    Given the same run with EXPORT_FORMAT=json
    When the run completes
    Then the income export is valid JSON with the same field names

  @AC-3
  Scenario: No export when the format is none
    Given EXPORT_FORMAT=none and a detected income source
    When the run completes
    Then no income file is written
    And the CLI still displays the income source

  @AC-4
  Scenario: No export when income detection is disabled
    Given INCOME_ACCOUNTS empty and EXPORT_FORMAT=csv
    When the run completes
    Then only the pattern export is written

  @AC-5
  Scenario: An ambiguous account appears as a row
    Given an income account with two qualifying payers
    When the run completes
    Then the income export contains a row for that account with status "ambiguous"
    And the row has an empty observed net income
    And both payers are named in the row

  @AC-6
  Scenario: An account with no qualifying candidate appears as a row
    Given an income account whose only candidate is quarterly
    When the run completes
    Then the income export contains a row for that account with status "no-qualifying-candidate"

  @AC-7
  Scenario: The written path is reported
    Given a completed income export
    When the run finishes
    Then the income file path is printed, on the same terms as FR-31

  @AC-8
  Scenario: Income is displayed before the review flow
    Given a run with a detected income source and pending suggestions
    When the CLI runs
    Then the income block is printed before the first suggestion prompt

  @AC-9
  Scenario: Nothing is created in Firefly III from the income path
    Given a run with income accounts configured and DRY_RUN unset
    When the run completes
    Then no bill-creation call is issued beyond those the approved withdrawal suggestions produce

  @AC-10
  Scenario: A new field flows through without an exporter change
    Given a field added to IncomeSource
    When the income export runs
    Then the new field appears in the output without editing the field list
