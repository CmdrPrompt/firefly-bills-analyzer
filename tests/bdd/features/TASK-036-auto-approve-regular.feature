# TASK-036: Add --auto-approve-regular CLI flag for non-irregular patterns
Feature: Auto-approve only regular recurring patterns with high confidence
  As a cash-flow analyst, I want to auto-approve only regular recurring bills
  (monthly, quarterly, half-yearly, yearly) when their confidence is high, so
  that irregular expenses are brought to my attention for verification rather
  than silently skipped or auto-rejected.

  @AC-1
  Scenario: Monthly pattern above confidence threshold is auto-approved
    Given a monthly recurring payment pattern with confidence at or above HIGH_CONFIDENCE_THRESHOLD
    When the review runs under --auto-approve-regular
    Then the pattern is automatically approved and printed as "[auto] approved: ..."

  @AC-2
  Scenario: Irregular pattern is presented for interactive review
    Given an irregular recurring payment pattern with confidence at or above HIGH_CONFIDENCE_THRESHOLD
    When the review runs under --auto-approve-regular
    Then the pattern is presented for interactive y/n/a/q review, not skipped

  @AC-3
  Scenario: Quarterly pattern below confidence threshold is presented for interactive review
    Given a quarterly recurring payment pattern with confidence below HIGH_CONFIDENCE_THRESHOLD
    When the review runs under --auto-approve-regular
    Then the pattern is presented for interactive y/n/a/q review, not skipped

  @AC-4
  Scenario: Existing --auto-approve flag still auto-approves and skips below-threshold entries
    Given a mixed list of recurring patterns: high-confidence and low-confidence
    When the review runs under the existing --auto-approve flag
    Then high-confidence patterns are auto-approved and low-confidence patterns are skipped (not presented for review)

  @AC-5
  Scenario: Both flags together produce mutual exclusivity error
    When the CLI is invoked with both --auto-approve and --auto-approve-regular flags
    Then argparse exits with an error message stating the flags are mutually exclusive
