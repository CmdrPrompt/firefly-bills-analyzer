# TASK-029 Export and display household spend (UC13)

## Status

in-progress

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

- [ ] 1. Scenario: Household spend is exported to its own file
      Given a run with one household spend record and `EXPORT_FORMAT=csv`
      When the run completes
      Then three export files exist and the household spend file contains one row with
      `record_type` `household-spend`

- [ ] 2. Scenario: One-off purchases are distinguishable
      Given a run with one household spend record and two one-off purchases
      When the run completes
      Then the file contains two rows with `record_type` `one-off`, each carrying its date,
      amount, payee, category, and source account

- [ ] 3. Scenario: JSON format is honored
      Given the same run with `EXPORT_FORMAT=json`
      When the run completes
      Then the household spend export is valid JSON with the same field names

- [ ] 4. Scenario: No export when the format is none
      Given `EXPORT_FORMAT=none` and household spend measured
      When the run completes
      Then no household spend file is written and the CLI still displays the figures

- [ ] 5. Scenario: No export when the feature is disabled
      Given `HOUSEHOLD_SPEND_CATEGORIES` is empty
      When the run completes
      Then no household spend file is written

- [ ] 6. Scenario: A record with too few months exports without a median
      Given a household spend record produced under FR-49e
      When the run completes
      Then its row carries its complete month count and an empty median

- [ ] 7. Scenario: An unmatched category reaches the file
      Given a configured category matching no transaction
      When the run completes
      Then it appears in the household spend export

- [ ] 8. Scenario: Tag correction counts are exported
      Given a run in which the include tag admitted two transactions and the exclude tag
      removed one
      When the run completes
      Then both counts appear in the export

- [ ] 9. Scenario: The written path is reported
      Given a completed household spend export
      When the run finishes
      Then the file path is printed, on the same terms as FR-31

- [ ] 10. Scenario: Household spend is displayed before the review flow
      Given a run with household spend measured and pending suggestions
      When the CLI runs
      Then the household spend block is printed before the first suggestion prompt

- [ ] 11. Scenario: A new field flows through without an exporter change
      Given a field added to the household spend record
      When the export runs
      Then the new field appears in the output without editing the field list

- [ ] `make bdd` and `make test` pass, with coverage >= the task-start baseline

## Out of scope

- Any consumer-side use of the file (SE-07).
- A web UI view. Contingent on Open Item #5.
- Merging this export into either of the other two.
- Writing anything back to Firefly III.

## Blockers

None.

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:** `git add docs/tasks/TASK-029-household-spend-export-and-display.md`
**Commit:** `git commit -m "docs(TASK-029): resolve TASK-028 blocker and start implementation"`
