# TASK-028 Aggregate household spend per account and category (UC13)

## Status

todo

## Requirements

**Binding:** FR-47a, FR-47b, FR-47c, FR-47d, FR-48a, FR-48b, FR-48c, FR-48d, FR-48e, FR-48f, FR-48g, FR-49a, FR-49b, FR-49c, FR-49d, FR-49e, FR-50, NFR-15, SE-08, SE-09, SE-10
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-002 (the withdrawal fetch this consumes), TASK-003
(pattern identification, whose output FR-48b subtracts), TASK-012 and TASK-014
(which define what a pattern's transactions are, after clustering)
**Blocked on:** nothing for the category-only path (FR-48g).
`firefly-python-api` REQ-012 / that repository's TASK-017 (`tags` on
`TransactionRead`) is required for FR-48d's include tag and FR-48e's exclude
tag only
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As the household member who buys the groceries, the children's clothes, and the
household supplies from my own account, I want that spending measured, so that a
cost split does not treat me as having contributed nothing simply because
groceries do not arrive on a monthly cycle.

## Description

New module `src/firefly_bills_analyzer/household_spend.py`, a pure consumer of
the withdrawal list already fetched for UC1, the identified patterns from UC2,
and `Config`. It performs no I/O, and issues no request to Firefly III at all
(NFR-15). This task ends with the aggregate in memory; exporting and displaying
it is TASK-029.

Configuration (`config.py`):

- `household_spend_categories: list[str]` from `HOUSEHOLD_SPEND_CATEGORIES`,
  comma-separated, empty disables the feature (FR-47a)
- `household_spend_one_off_threshold: float` from
  `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD`, default 2000 (FR-47b)
- `household_spend_min_months: int` from `HOUSEHOLD_SPEND_MIN_MONTHS`,
  default 3 (FR-47c)
- `household_spend_include_tag: str | None` and
  `household_spend_exclude_tag: str | None` from their respective variables,
  both optional (FR-47d)

Qualification, in this order:

1. Drop every withdrawal carrying the exclude tag (FR-48e). This runs first and
   is absolute. The tag that removes money from a member's claimed contribution
   must not be overridable by anything the application infers.
2. Admit a withdrawal whose category is a household spend category, or which
   carries the include tag (FR-48d).
3. Drop every withdrawal belonging to an identified recurring pattern (FR-48b).
4. Set aside every withdrawal above the one-off threshold (FR-48c).

FR-48b is the step most likely to be got wrong. The comparison must be against
the transactions the pattern was actually built from, after source-account
partitioning (FR-32d) and amount clustering (FR-32a), not against a
payee-name match. A subscription sitting in a household category that is
counted both as a pattern and as household spend inflates one member's
contribution by exactly the amount of a bill they are already credited for.
Identity should be by the transaction's own identity, not by reconstructing a
match from its fields.

Aggregation:

- Sum the retained withdrawals per `(source_name, category_name, year-month)`
  (FR-49a)
- Drop the monthly totals of months not falling entirely inside the analysis
  window (FR-49b). Both the first and last month of the window are partial by
  construction, since the window starts and ends mid-month
- The reported figure per `(source_name, category_name)` is the median of the
  surviving monthly totals (FR-49c), with mean, min, max, and month count
  alongside it (FR-49d)
- Fewer than `household_spend_min_months` complete months yields a record with
  the month count and no median (FR-49e)
- A configured category matching no transaction is reported as unmatched
  (FR-50)

A month in which a qualifying account and category had no spending counts as a
zero month, not as a missing one. Otherwise an account that buys groceries in
nine months out of twelve reports the median of its nine active months, which
overstates its monthly cost.

FR-48g keeps the whole feature working with no tags configured, and without
requiring `tags` to be present on the record at all, so this task can merge
before `firefly-python-api` REQ-012 lands. Guard the tag reads accordingly.

FR-48f counts what each tag moved; carry those two counts on the result for
TASK-029 to display.

## Branch

**Branch name:** `task/028-household-spend-aggregation`
**Switch/create:** `git checkout -b task/028-household-spend-aggregation`
**Make target:** `make branch-task f=TASK-028`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-028-household-spend-aggregation.feature

- [ ] 1. Scenario: Groceries bought several times a month are measured
      Given twelve complete months of grocery withdrawals from one account, several per month
      When household spend is aggregated
      Then one record is produced for that account and category, with a median of the twelve
      monthly totals

- [ ] 2. Scenario: The figure is the median, not the mean
      Given eleven monthly totals of 5000 and one of 20000
      When household spend is aggregated
      Then the reported median is 5000 and the reported mean is higher than it

- [ ] 3. Scenario: A month with no spending counts as zero
      Given nine months with grocery spending and three complete months with none
      When household spend is aggregated
      Then twelve monthly totals contribute to the median, three of them zero

- [ ] 4. Scenario: A subscription already counted as a pattern is not counted twice
      Given a monthly subscription in a household spend category that UC2 identified as a pattern
      When household spend is aggregated
      Then none of that subscription's transactions appear in any monthly total

- [ ] 5. Scenario: A large purchase is set aside
      Given a single withdrawal of 15000 in a household category and a threshold of 2000
      When household spend is aggregated
      Then that withdrawal appears as a one-off purchase with its date, amount, payee, category,
      and source account, and contributes to no monthly total

- [ ] 6. Scenario: Partial months at the window edges are dropped
      Given an analysis window starting and ending mid-month
      When household spend is aggregated
      Then the first and last calendar months contribute no monthly total

- [ ] 7. Scenario: The exclude tag removes a transaction from a household category
      Given a withdrawal in a household spend category carrying the exclude tag
      When household spend is aggregated
      Then it contributes to no monthly total and is counted in the exclude-tag count

- [ ] 8. Scenario: The include tag admits a transaction from a personal category
      Given a withdrawal in a category that is not a household spend category, carrying the
      include tag
      When household spend is aggregated
      Then it contributes to its account's monthly total and is counted in the include-tag count

- [ ] 9. Scenario: The exclude tag beats the include tag
      Given a withdrawal carrying both override tags
      When household spend is aggregated
      Then it contributes to no monthly total

- [ ] 10. Scenario: No tags configured leaves category behavior intact
      Given neither override tag is configured, and records with no `tags` field
      When household spend is aggregated
      Then qualification is by category alone and no error is raised

- [ ] 11. Scenario: Too few complete months yields no median
      Given two complete months of data and `HOUSEHOLD_SPEND_MIN_MONTHS` of 3
      When household spend is aggregated
      Then the record carries a month count of 2 and no median figure

- [ ] 12. Scenario: An unmatched category is reported
      Given a configured category appearing on no transaction in the window
      When household spend is aggregated
      Then that category is reported as unmatched

- [ ] 13. Scenario: Two accounts are measured independently
      Given household spending from two different source accounts
      When household spend is aggregated
      Then each account and category pair has its own record

- [ ] 14. Scenario: The feature is inert when unconfigured
      Given `HOUSEHOLD_SPEND_CATEGORIES` is empty
      When the analysis runs
      Then no aggregation is performed, no request is issued, and the run's behavior is
      identical to today's

- [ ] 15. Hypothesis property test: for any set of withdrawals, the sum of every monthly total
      plus the sum of the one-off purchases plus the sum of the excluded transactions equals
      the sum of all qualifying withdrawals; no amount is created or lost by the partitioning

- [ ] 16. Hypothesis property test: no transaction belonging to an identified pattern appears in
      any monthly total, for any combination of categories and tags

- [ ] `make bdd` and `make test` pass, with coverage >= the task-start baseline

## Out of scope

- Exporting or displaying the result (TASK-029).
- Any split of a single transaction between household and personal (SE-09).
- Inferring which categories are household spending (SE-08).
- Writing or suggesting tags in Firefly III (SE-10).
- Any use of these figures in a cost split (SE-07); that lives in
  `firefly-household-splitter`.
- Fetching anything. The withdrawals are already in memory (NFR-15).

## Blockers

None for the category path. FR-48d's include tag and FR-48e's exclude tag
require `tags` on `TransactionRead`, which is `firefly-python-api` REQ-012 /
TASK-017 and not yet implemented. Implement the category path first and guard
the tag reads so the module works either way; complete the tag scenarios once
the vendored `lib/firefly-python-api` copy has been re-synced.

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
