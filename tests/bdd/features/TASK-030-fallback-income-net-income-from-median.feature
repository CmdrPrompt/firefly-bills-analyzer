# TASK-030: Fallback income observed_net_income when latest occurrence deviates from median
Feature: Fallback income observed_net_income when latest occurrence deviates from median
  As a cash flow planner, I want the application to handle small income
  anomalies gracefully, so that a reimbursement or small allowance landing
  on an income account after the month's main salary does not override the
  observed net income figure with that anomaly's amount.

  @AC-1
  Scenario: Normal case: latest occurrence does not deviate from median
    Given an income account with occurrences 1000, 1000, 1000, 1010 and INCOME_VARIANCE_TOLERANCE of 0.10
    When the application detects the income source
    Then the observed net income is 1010, the latest occurrence
    And the observed date is the date of the occurrence with amount 1010
    And outlier_count is 0

  @AC-2
  Scenario: Latest occurrence deviates; fallback to previous non-deviating
    Given an income account with three dated occurrences: 2026-07-01 amount 1000, 2026-08-01 amount 1000, 2026-09-01 amount 50, tolerance 0.10
    When the application detects the income source
    Then the observed net income is 1000, from 2026-08-01
    And the observed date matches 2026-08-01
    And outlier_count is 1

  @AC-3
  Scenario: All occurrences deviate from median except one
    Given an income account with occurrences 1000, 100, 100, 100 and INCOME_VARIANCE_TOLERANCE of 0.10
    When the application detects the income source
    Then the observed net income is 100, the most recent non-deviating from median
    And outlier_count is 1
    And amount_min, amount_max, amount_mean include all four occurrences

  @AC-4
  Scenario: Variance figures always span all occurrences
    Given an income account with occurrences 1000, 1000, 1000, 50 and INCOME_VARIANCE_TOLERANCE of 0.10
    When the application detects the income source
    Then amount_min is 50, amount_max is 1000, amount_mean is 762.5
    And occurrences count is 4
    And outlier_count measures deviation from the selected observed_net_income only
