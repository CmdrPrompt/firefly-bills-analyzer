# TASK-029: Export and display household spend (UC13)
Feature: Export and display household spend
  As a user, I want the measured household spending in a file next to the
  other exports, with the large one-off purchases listed separately, so that
  a downstream split can use the monthly figure while we settle the sofa on
  its own terms.

  @AC-1
  Scenario: Household spend is exported to its own file
    Given a run with one household spend record and EXPORT_FORMAT=csv
    When the run completes
    Then three export files exist
    And the household spend file contains one row with record_type "household-spend"

  @AC-2
  Scenario: One-off purchases are distinguishable
    Given a run with one household spend record and two one-off purchases
    When the run completes
    Then the household spend file contains two rows with record_type "one-off"
    And each one-off row carries its date, amount, payee, category, and source account

  @AC-3
  Scenario: JSON format is honored
    Given the same run with EXPORT_FORMAT=json
    When the run completes
    Then the household spend export is valid JSON with the same field names

  @AC-4
  Scenario: No export when the format is none
    Given EXPORT_FORMAT=none and household spend measured
    When the run completes
    Then no household spend file is written
    And the CLI still displays the household spend figures

  @AC-5
  Scenario: No export when the feature is disabled
    Given HOUSEHOLD_SPEND_CATEGORIES is empty
    When the run completes
    Then no household spend file is written

  @AC-6
  Scenario: A record with too few months exports without a median
    Given a household spend record produced under FR-49e
    When the run completes
    Then its row carries its complete month count and an empty median

  @AC-7
  Scenario: An unmatched category reaches the file
    Given a configured category matching no transaction
    When the run completes
    Then it appears in the household spend export

  @AC-8
  Scenario: Tag correction counts are exported
    Given a run in which the include tag admitted two transactions and the exclude tag removed one
    When the run completes
    Then both counts appear in the export

  @AC-9
  Scenario: The written path is reported
    Given a completed household spend export
    When the run finishes
    Then the household spend file path is printed, on the same terms as FR-31

  @AC-10
  Scenario: Household spend is displayed before the review flow
    Given a run with household spend measured and pending suggestions
    When the CLI runs
    Then the household spend block is printed before the first suggestion prompt

  @AC-11
  Scenario: A new field flows through without an exporter change
    Given a field added to the household spend record
    When the export runs
    Then the new field appears in the output without editing the field list
