# TASK-033: Per-category one-off purchase thresholds (FR-47e, FR-47f, FR-48c, FR-51c)
Feature: Per-category one-off purchase thresholds
  As a household budget manager, I want to set different one-off thresholds
  for different spending categories, so that a 2,000-2,500 kr grocery
  purchase is treated as routine household spend in "Mat och hushåll" while
  a car repair above a higher threshold is still flagged as a settlement in
  "Transport".

  @AC-1
  Scenario: Withdrawal under category override threshold is included in household spend
    Given a withdrawal in a category with a configured threshold override, for an amount above the default threshold but below the override
    When household spend is aggregated
    Then the withdrawal is counted in the household spend monthly totals

  @AC-2
  Scenario: Withdrawal under default threshold in unconfigured category is included in household spend
    Given a withdrawal in a category with no threshold override, for an amount under the default threshold, while other categories have overrides configured
    When household spend is aggregated
    Then the withdrawal is counted in the household spend monthly totals

  @AC-3
  Scenario: Exported one-off purchase includes the threshold amount that excluded it
    Given a one-off purchase excluded by its category's threshold override
    When the household spend export runs
    Then the exported one-off row carries the threshold amount that excluded it

  @AC-4
  Scenario: Unmatched threshold override category is reported
    Given a threshold override configured for a category absent from the household spend categories
    When household spend is aggregated
    Then the category is reported as an unmatched threshold override
