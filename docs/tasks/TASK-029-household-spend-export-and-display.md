# TASK-029 Export and display household spend (UC13)

## Status

done

## Requirements

**Binding:** FR-51a, FR-51b, FR-51c, FR-51d, FR-52
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-028 (the aggregate this writes), TASK-005 (the CLI flow
this inserts into), TASK-011 (FR-31's file path reporting, which FR-51d
mirrors), TASK-027 (the second export file, whose naming pattern this follows)
**Blocked on:** nothing (TASK-028 is done and merged, commit 3cde68e).
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user, I want the measured household spending in a file next to the other
exports, with the large one-off purchases listed separately, so that a
downstream split can use the monthly figure while we settle the sofa on its own
terms.

## Description

Extend `exporter.py` with a household spend export, and `cli.py` with the
display required by FR-52.

This is the third export file. Name it on the same timestamp pattern as the
others, with a `household-spend` discriminator, e.g.
`firefly-household-spend-20260802T162519.csv`. Three files rather than one
merged file, for the same reason TASK-027 gave: the record shapes have nothing
in common and a consumer reads them for different purposes.

Household spend rows (FR-51b): `source_account_name`, `category_name`,
`median_monthly`, `mean_monthly`, `min_monthly`, `max_monthly`,
`complete_months`. A record produced under FR-49e carries its month count and
an empty median.

One-off rows (FR-51c): `date`, `amount`, `destination_name`, `category_name`,
`source_account_name`. They must be distinguishable from household spend rows;
use a `record_type` column (`household-spend` or `one-off`) rather than
relying on which fields are empty, so a consumer's parse does not depend on
absence.

Also export the unmatched categories from FR-50 and the two tag counts from
FR-48f, so that a misspelled category and the extent of manual tag correction
are both visible in the file rather than only on screen.

Derive the field list from the dataclasses rather than hard-coding it, matching
`_FIELDNAMES` for the pattern export and the income export.

CLI display (FR-52): print the household spend figures, the one-off purchases,
and anything reported under FR-49e or FR-50, before the review flow. Reuse the
existing table formatting; do not introduce a third style.

## Branch

**Branch name:** `task/029-household-spend-export-and-display`
**Switch/create:** `git checkout -b task/029-household-spend-export-and-display`
**Make target:** `make branch-task f=TASK-029`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-029-household-spend-export-and-display.feature

- [x] 1. Scenario: Household spend is exported to its own file
      Given a run with one household spend record and `EXPORT_FORMAT=csv`
      When the run completes
      Then three export files exist and the household spend file contains one row with
      `record_type` `household-spend`

- [x] 2. Scenario: One-off purchases are distinguishable
      Given a run with one household spend record and two one-off purchases
      When the run completes
      Then the file contains two rows with `record_type` `one-off`, each carrying its date,
      amount, payee, category, and source account

- [x] 3. Scenario: JSON format is honored
      Given the same run with `EXPORT_FORMAT=json`
      When the run completes
      Then the household spend export is valid JSON with the same field names

- [x] 4. Scenario: No export when the format is none
      Given `EXPORT_FORMAT=none` and household spend measured
      When the run completes
      Then no household spend file is written and the CLI still displays the figures

- [x] 5. Scenario: No export when the feature is disabled
      Given `HOUSEHOLD_SPEND_CATEGORIES` is empty
      When the run completes
      Then no household spend file is written

- [x] 6. Scenario: A record with too few months exports without a median
      Given a household spend record produced under FR-49e
      When the run completes
      Then its row carries its complete month count and an empty median

- [x] 7. Scenario: An unmatched category reaches the file
      Given a configured category matching no transaction
      When the run completes
      Then it appears in the household spend export

- [x] 8. Scenario: Tag correction counts are exported
      Given a run in which the include tag admitted two transactions and the exclude tag
      removed one
      When the run completes
      Then both counts appear in the export

- [x] 9. Scenario: The written path is reported
      Given a completed household spend export
      When the run finishes
      Then the file path is printed, on the same terms as FR-31

- [x] 10. Scenario: Household spend is displayed before the review flow
      Given a run with household spend measured and pending suggestions
      When the CLI runs
      Then the household spend block is printed before the first suggestion prompt

- [x] 11. Scenario: A new field flows through without an exporter change
      Given a field added to the household spend record
      When the export runs
      Then the new field appears in the output without editing the field list

- [x] `make bdd` and `make test` pass, with coverage >= the task-start baseline

## Out of scope

- Any consumer-side use of the file (SE-07).
- A web UI view. Contingent on Open Item #5.
- Merging this export into either of the other two.
- Writing anything back to Firefly III.

## Blockers

None.

## Completion

**Date:** 2026-08-03
**Summary:** Wired TASK-028's household spend aggregation into the CLI pipeline and export
layer (UC13, FR-51a-d, FR-52). `__main__.py` now calls `household_spend.aggregate_household_spend`
over the raw, pre-filter withdrawal list (per FR-48a), prints the household spend figures,
one-off purchases, unmatched categories (FR-50), and tag correction counts (FR-48f) before the
recurring-payment review flow, and — when the feature is enabled and `EXPORT_FORMAT` is not
`none` — writes them to a third export file (`firefly-household-spend-<timestamp>.<ext>`),
printing its path on the same terms as FR-31. Added `exporter.export_household_spend()`,
deriving its field list from `HouseholdSpendRecord`/`OneOffPurchase`'s own dataclass fields
via rename maps (mirroring `_INCOME_FIELDNAMES`'s derivation pattern), with household-spend,
one-off, unmatched-category, and tag-counts rows sharing one file and distinguished by a
`record_type` column (FR-51c) rather than by which fields are empty. Wrote
`tests/bdd/features/TASK-029-household-spend-export-and-display.feature` (11 scenarios,
@AC-1..@AC-11) and its step bindings first (outside-in), confirmed red, then implemented to
green, plus Hypothesis-driven unit tests in `tests/test_exporter.py`. After an independent
Test Design Review (Farley Index 8.3/10) flagged two real findings — CSV round-trip property
tests asserting only one field instead of verifying the values they claimed to preserve, and
missing JSON-format coverage for the unmatched-category/tag-counts rows — both were fixed:
the round-trip tests now assert every numeric/string field with `math.isclose` tolerance for
floats, and JSON-equivalent tests were added for both row kinds. Implementation was delegated
to an Implementation Worker subagent in an isolated worktree; its report was independently
verified against ground truth (diff review, re-running `make bdd`/`make test`/`make lint`)
before merging. Out of scope items (consumer-side use of the file, web UI view, merging this
export into either of the other two, writing back to Firefly III) were left untouched, as
specified.
**Files changed:**
- `src/firefly_bills_analyzer/exporter.py` - modified (added `export_household_spend`)
- `src/firefly_bills_analyzer/__main__.py` - modified (wired household spend into the pipeline,
  display, and export)
- `tests/bdd/features/TASK-029-household-spend-export-and-display.feature` - created
- `tests/bdd/steps/test_task_029_steps.py` - created
- `tests/test_exporter.py` - modified (Hypothesis strategies and unit tests for
  `export_household_spend`)
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-029-household-spend-export-and-display.md` - modified (Status, Blockers,
  acceptance criteria, Completion)
**Branch:** `git checkout task/029-household-spend-export-and-display`
**Stage:** `git add src/firefly_bills_analyzer/exporter.py src/firefly_bills_analyzer/__main__.py tests/bdd/features/TASK-029-household-spend-export-and-display.feature tests/bdd/steps/test_task_029_steps.py tests/test_exporter.py CHANGELOG.md docs/tasks/TASK-029-household-spend-export-and-display.md`
**Commit:** `git commit -m "TASK-029: export and display household spend (UC13)"`
