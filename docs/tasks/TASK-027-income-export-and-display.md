# TASK-027 Export and display income sources (UC12)

## Status

done

## Requirements

**Binding:** FR-45a, FR-45b, FR-45c, FR-45d, FR-46, SE-04
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-026 (the `IncomeSource` and `IncomeAccountIssue` records
this writes), TASK-005 (the CLI flow this inserts into), TASK-011 (FR-31's file
path reporting, which FR-45d mirrors)
**Blocked on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user, I want the detected income written to a file next to the recurring
payment export, so that a downstream tool can consume both without me copying
numbers between them, and so that an account where detection failed is visible
in the file rather than merely absent from it.

## Description

Extend `exporter.py` with an income export, and `cli.py` with the display
required by FR-46.

Export (FR-45a): written only when income detection is enabled and
`EXPORT_FORMAT` is not `none`, in that same format, to a separate file. Name it
on the same timestamp pattern the existing export uses, with an `income`
discriminator, e.g. `firefly-income-20260802T162519.csv`. Two files, never one
merged file: the two record shapes have nothing in common, and a consumer reads
them for different purposes.

Fields (FR-45b): `income_account`, `payer`, `observed_net_income`,
`observed_date`, `occurrences`, `median_interval_days`, `amount_min`,
`amount_max`, `amount_mean`, `outlier_count`.

Issue rows (FR-45c): the accounts reported under FR-42b and FR-42c appear in
the same file, carrying `income_account`, an empty `payer`, an empty
`observed_net_income`, and a `status` column giving the reason
(`no-qualifying-candidate` or `ambiguous`) plus the candidate payers that were
considered. An income source row carries `status` `ok`. A member whose income
could not be determined must be visible to a consumer as a row, not as silence.

Derive the field list from the dataclass rather than hard-coding it, matching
how `_FIELDNAMES` is built for the pattern export, so a later field addition
flows through without touching the exporter.

Path reporting (FR-45d): print the written path, on the same terms as FR-31.

CLI display (FR-46): print the income sources and the issue accounts before the
review flow, so the user sees a failed detection before spending attention on
bill approvals. Reuse the existing formatting helpers rather than introducing a
second table style.

SE-04 holds by construction here: nothing in this path constructs a bill
payload. Add the assertion anyway, as a test that a run with income accounts
configured and `DRY_RUN` unset issues no additional creation call.

## Branch

**Branch name:** `task/027-income-export-and-display`
**Switch/create:** `git checkout -b task/027-income-export-and-display`
**Make target:** `make branch-task f=TASK-027`

## Acceptance criteria (Gherkin)

- [x] Scenario: Income is exported to its own file
      Given a run with one detected income source and `EXPORT_FORMAT=csv`
      When the run completes
      Then two files are written, the pattern export and an income export, and
      the income file contains one row with `status` `ok`

- [x] Scenario: JSON format is honored
      Given the same run with `EXPORT_FORMAT=json`
      When the run completes
      Then the income export is valid JSON with the same field names

- [x] Scenario: No export when the format is none
      Given `EXPORT_FORMAT=none` and a detected income source
      When the run completes
      Then no income file is written and the CLI still displays the income source

- [x] Scenario: No export when income detection is disabled
      Given `INCOME_ACCOUNTS` empty and `EXPORT_FORMAT=csv`
      When the run completes
      Then only the pattern export is written

- [x] Scenario: An ambiguous account appears as a row
      Given an income account with two qualifying payers
      When the run completes
      Then the income export contains a row for that account with `status`
      `ambiguous`, an empty observed net income, and both payers named

- [x] Scenario: An account with no qualifying candidate appears as a row
      Given an income account whose only candidate is quarterly
      When the run completes
      Then the income export contains a row for that account with `status`
      `no-qualifying-candidate`

- [x] Scenario: The written path is reported
      Given a completed income export
      When the run finishes
      Then the income file path is printed, on the same terms as FR-31

- [x] Scenario: Income is displayed before the review flow
      Given a run with a detected income source and pending suggestions
      When the CLI runs
      Then the income block is printed before the first suggestion prompt

- [x] Scenario: Nothing is created in Firefly III from the income path
      Given a run with income accounts configured and `DRY_RUN` unset
      When the run completes
      Then no bill-creation call is issued beyond those the approved
      withdrawal suggestions produce

- [x] Scenario: A new field flows through without an exporter change
      Given a field added to `IncomeSource`
      When the income export runs
      Then the new field appears in the output without editing the field list

- [x] `make lint && make test` pass with coverage >= the task-start baseline

## Out of scope

- Any consumer-side use of the exported file. `firefly-household-splitter`
  owns that, per SE-07.
- A web UI view of income. Contingent on Open Item #5 like every other web
  surface.
- Merging the income export into the pattern export.
- Writing income back to Firefly III in any form.

## Blockers

None

## Completion

**Date:** 2026-08-03
**Summary:** Added `exporter.export_income()`, writing income sources and
income-account issues (FR-42b/FR-42c) to a `firefly-income-*.csv/json` file
separate from the pattern export, gated on `EXPORT_FORMAT != "none"` and on
the detected `IncomeResult` carrying at least one source or issue. The field
list (`_INCOME_FIELDNAMES`) is derived from `IncomeSource`'s dataclass
fields plus `status`, mirroring how `_FIELDNAMES` is derived for the pattern
export, so a later field addition to `IncomeSource` flows through
unmodified. A source row carries `status` `ok`; an issue row carries an
empty `payer`/`observed_net_income` and a `status` naming the reason plus
the candidate payers considered. Wired `income.detect_income()` into
`__main__.main()`, printing the income sources and issue accounts (FR-46)
before the review flow, and printing the written income file path on the
same terms as the existing FR-31 pattern-export path message (FR-45d). SE-04
holds by construction: no code on this path constructs a bill payload; the
AC-9 scenario asserts `create_bills` is called exactly once (the withdrawal
side's own call) even with income accounts configured and `DRY_RUN` unset.

**Files changed:**

- `src/firefly_bills_analyzer/exporter.py` - added `export_income()` and its
  CSV/JSON helpers, deriving `_INCOME_FIELDNAMES` from `IncomeSource`
- `src/firefly_bills_analyzer/__main__.py` - wired `income.detect_income()`
  into `main()`, added `_print_income()`, `_format_income_source()`,
  `_format_income_issue()` (FR-46), and `_default_income_export_path()`
  (FR-45a/FR-45d)
- `tests/test_exporter.py` - added `TestIncomeUnsupportedFormat` alongside
  the Test Writer's existing `export_income` coverage, for parity with
  `export()`'s unsupported-format test
- `CHANGELOG.md` - added a behavior-first entry for this task
- `docs/tasks/TASK-027-income-export-and-display.md` - Completion section
**Branch:** `git checkout task/027-income-export-and-display`
**Stage:** `git add src/firefly_bills_analyzer/exporter.py src/firefly_bills_analyzer/__main__.py tests/test_exporter.py CHANGELOG.md docs/tasks/TASK-027-income-export-and-display.md`
**Commit:** `git commit -m "Export and display detected income sources and issue accounts (TASK-027)"`
