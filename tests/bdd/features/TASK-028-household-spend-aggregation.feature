# TASK-028: Aggregate household spend per account and category (UC13)
Feature: Aggregate household spend per account and category
  As the household member who buys the groceries, the children's clothes, and
  the household supplies from my own account, I want that spending measured,
  so that a cost split does not treat me as having contributed nothing simply
  because groceries do not arrive on a monthly cycle.

  @AC-1
  Scenario: Groceries bought several times a month are measured
    Given twelve complete months of grocery withdrawals from one account, several per month
    When household spend is aggregated
    Then one record is produced for that account and category, with a median of the twelve monthly totals

  @AC-2
  Scenario: The figure is the median, not the mean
    Given eleven monthly totals of 5000 and one of 20000
    When household spend is aggregated
    Then the reported median is 5000 and the reported mean is higher than it

  @AC-3
  Scenario: A month with no spending counts as zero
    Given nine months with grocery spending and three complete months with none
    When household spend is aggregated
    Then twelve monthly totals contribute to the median, three of them zero

  @AC-4
  Scenario: A subscription already counted as a pattern is not counted twice
    Given a monthly subscription in a household spend category that UC2 identified as a pattern
    When household spend is aggregated
    Then none of that subscription's transactions appear in any monthly total

  @AC-5
  Scenario: A large purchase is set aside
    Given a single withdrawal of 15000 in a household category and a threshold of 2000
    When household spend is aggregated
    Then that withdrawal appears as a one-off purchase with its date, amount, payee, category, and source account
    And it contributes to no monthly total

  @AC-6
  Scenario: Partial months at the window edges are dropped
    Given an analysis window starting and ending mid-month
    When household spend is aggregated
    Then the first and last calendar months contribute no monthly total

  @AC-7
  Scenario: The exclude tag removes a transaction from a household category
    Given a withdrawal in a household spend category carrying the exclude tag
    When household spend is aggregated
    Then it contributes to no monthly total and is counted in the exclude-tag count

  @AC-8
  Scenario: The include tag admits a transaction from a personal category
    Given a withdrawal in a category that is not a household spend category, carrying the include tag
    When household spend is aggregated
    Then it contributes to its account's monthly total and is counted in the include-tag count

  @AC-9
  Scenario: The exclude tag beats the include tag
    Given a withdrawal carrying both override tags
    When household spend is aggregated
    Then it contributes to no monthly total

  @AC-10
  Scenario: No tags configured leaves category behavior intact
    Given neither override tag is configured, and records with no tags field
    When household spend is aggregated
    Then qualification is by category alone and no error is raised

  @AC-11
  Scenario: Too few complete months yields no median
    Given two complete months of data and a minimum of three complete months required
    When household spend is aggregated
    Then the record carries a month count of 2 and no median figure

  @AC-12
  Scenario: An unmatched category is reported
    Given a configured category appearing on no transaction in the window
    When household spend is aggregated
    Then that category is reported as unmatched

  @AC-13
  Scenario: Two accounts are measured independently
    Given household spending from two different source accounts
    When household spend is aggregated
    Then each account and category pair has its own record

  @AC-14
  Scenario: The feature is inert when unconfigured
    Given the household spend categories are empty
    When household spend is aggregated
    Then no aggregation is performed and the result carries no records, one-offs, or unmatched categories
