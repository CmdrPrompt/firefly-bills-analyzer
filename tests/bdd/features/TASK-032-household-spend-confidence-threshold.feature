# TASK-032: Household spend excludes only high-confidence recurring patterns (FR-48b, UC13)
Feature: Household spend excludes only high-confidence recurring patterns
  As a user with groceries, utilities, and other household costs bought across
  multiple transactions that UC2 cannot reliably cluster, I want those real
  ongoing costs measured as household spend rather than silently excluded
  because they belong to a low-confidence pattern, so that my actual cash
  flow is visible in the export.

  @AC-1
  Scenario: High-confidence recurring pattern excludes withdrawal from household spend
    Given a monthly subscription in a household spend category with steady amounts and dates, forming a high-confidence pattern
    When household spend is aggregated
    Then none of the subscription's withdrawals appear in any monthly total

  @AC-2
  Scenario: Low-confidence pattern allows withdrawal into household spend
    Given two irregular withdrawals to the same payee in a household spend category, forming a low-confidence pattern
    When household spend is aggregated
    Then the withdrawals are counted in the household spend monthly totals

  @AC-3
  Scenario: Large single-cluster payee with varying amounts is measured as household spend
    Given many withdrawals to one payee and account in a household spend category, with varying amounts on distinct dates and no same-day co-occurrence
    When household spend is aggregated
    Then all of the withdrawals are counted in the household spend monthly totals
