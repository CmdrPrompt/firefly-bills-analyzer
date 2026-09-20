# TASK-037: Multi-format export support (FR-53a, FR-53b, FR-53c, FR-53d, FR-29, FR-31)
Feature: Export to multiple formats simultaneously via comma-separated list
  As a cash-flow analyst, I want to configure EXPORT_FORMAT as a
  comma-separated list (e.g. csv,json) to export all analysis reports in
  multiple formats simultaneously, so that I can use whichever format suits
  my downstream tools without re-running the analysis.

  @AC-1
  Scenario: Single CSV export works as before
    Given EXPORT_FORMAT=csv configured and a dry-run analysis with patterns, income sources, and household spend to export
    When the analysis runs and exports complete
    Then patterns are exported to a CSV file with .csv extension
    And income sources are exported to a CSV file with .csv extension
    And household spend is exported to a CSV file with .csv extension
    And the path to each file is printed to the terminal

  @AC-2
  Scenario: Single JSON export works as before
    Given EXPORT_FORMAT=json configured and a dry-run analysis with patterns, income sources, and household spend to export
    When the analysis runs and exports complete
    Then patterns are exported to a JSON file with .json extension
    And income sources are exported to a JSON file with .json extension
    And household spend is exported to a JSON file with .json extension
    And the path to each file is printed to the terminal

  @AC-3
  Scenario: Multiple formats export each report in all formats
    Given EXPORT_FORMAT=csv,json configured and a dry-run analysis with patterns, income sources, and household spend to export
    When the analysis runs and exports complete
    Then patterns are exported to both a .csv file and a .json file
    And income sources are exported to both a .csv file and a .json file
    And household spend is exported to both a .csv file and a .json file
    And the paths to all six files are printed to the terminal

  @AC-4
  Scenario: Invalid config: none combined with other format is rejected
    Given EXPORT_FORMAT=csv,none configured
    When the application is invoked
    Then startup fails with a ConfigError stating none cannot be combined with other export formats

  @AC-5
  Scenario: Invalid config: unsupported format is rejected and named
    Given EXPORT_FORMAT=yaml configured
    When the application is invoked
    Then startup fails with a ConfigError naming yaml as an unsupported export format

  @AC-6
  Scenario: Invalid config: duplicate format is rejected and named
    Given EXPORT_FORMAT=csv,csv configured
    When the application is invoked
    Then startup fails with a ConfigError naming csv as appearing more than once in EXPORT_FORMAT

  @AC-7
  Scenario: Each exported file path is printed
    Given EXPORT_FORMAT=csv configured and a dry-run analysis with patterns and income sources to export
    When the analysis runs
    Then the printed output includes the path to the patterns export file
    And the printed output includes the path to the income export file

  @AC-8
  Scenario: Help text documents comma-separated export syntax
    When the application is invoked with --help
    Then the help text shows EXPORT_FORMAT as accepting csv, json, none, or a comma-separated list such as csv,json
