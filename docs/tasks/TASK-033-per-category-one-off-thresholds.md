# TASK-033 Per-category one-off purchase thresholds (FR-47e, FR-47f, FR-48c, FR-51c)

## Status

todo

## Requirements

**Binding:** FR-47b, FR-47e, FR-47f, FR-48c, FR-51c, UC13
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-028, TASK-032
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a household budget manager, I want to set different one-off thresholds for
different spending categories, so that a 2,000–2,500 kr grocery purchase is
treated as routine household spend in "Mat och hushåll" while a car repair
above a higher threshold is still flagged as a settlement in "Transport".

## Description

Currently, `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD` applies uniformly to all
household-spend categories. Real user data shows this misclassifies ordinary
grocery runs costing 2,000–2,500 kr as one-off purchases. The fix introduces
per-category threshold overrides via `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS`
(e.g. `Mat och hushåll:3000,Transport:6000`), while preserving backward
compatibility: categories without an override use the default
`HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD`.

Implementation surface:
- `config.py`: add `household_spend_one_off_thresholds: dict[str, float]` field
  and parser for `category:amount` comma-separated pairs (a format not yet used
  in this codebase's config layer)
- `household_spend.py`:
  - `OneOffPurchase` dataclass: add `threshold: float` field
  - `_split_one_off_purchases()`: resolve per-category thresholds (override or
    default), include threshold in each `OneOffPurchase`
  - Add unmatched-threshold-override detection (FR-47f) and surface in
    `HouseholdSpendResult` alongside or separate from `unmatched_categories`,
    per implementer's judgment on the cleanest shape
- `exporter.py`: the rename and fieldname tables flow through automatically
  once `OneOffPurchase.threshold` exists
- `__main__.py`: `_format_one_off_purchase()` displays the threshold

## Branch

**Branch name:** `task/033-per-category-one-off-thresholds`
**Switch/create:** `git checkout -b task/033-per-category-one-off-thresholds`
**Make target:** `make branch-task f=TASK-033`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature

- [ ] 1. Scenario: A withdrawal in a category with an explicit threshold override uses that override, not the default
      See tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature: Scenario "Withdrawal under category override threshold is included in household spend"

- [ ] 2. Scenario: A withdrawal in a category without an override uses the default threshold
      See tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature: Scenario "Withdrawal under default threshold in unconfigured category is included in household spend"

- [ ] 3. Scenario: Each exported one-off purchase record carries the threshold amount that excluded it
      See tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature: Scenario "Exported one-off purchase includes the threshold amount that excluded it"

- [ ] 4. Scenario: A category named in the override mapping but absent from household spend categories is reported as an unmatched threshold override
      See tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature: Scenario "Unmatched threshold override category is reported"

- [ ] 5. `make lint && make test && make bdd` pass with coverage >= the TASK-032 baseline

## Out of scope

- Changing recurring pattern identification or confidence calculation (UC2, FR-27)
- Modifying `_classify_frequency()` or the frequency bucket logic
- Adding fields to `HouseholdSpendRecord` or `RecurringPattern`
- Web UI display of threshold overrides (deferred pending Open Item #5)

## Blockers

None

## Completion

**Date:** 2026-08-04
**Summary:** `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS` (comma-separated
`category:amount` pairs) lets each household spend category override the
default `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD`. `Config` parses the mapping via a
new `key:value` comma-pair parser (malformed entries skipped silently, like
`_csv()` does for blanks). `_split_one_off_purchases()` resolves each
transaction's threshold from the override dict, falling back to the default,
and `OneOffPurchase` carries that resolved `threshold` on every record.
`_unmatched_threshold_overrides()` reports (FR-47f) an override category
absent from `HOUSEHOLD_SPEND_CATEGORIES`, surfaced via
`HouseholdSpendResult.unmatched_threshold_overrides`, printed in the CLI, and
exported as `record_type == "unmatched-threshold-override"` rows. Fixed a
copy-paste bug in a shared BDD step (`test_task_033_steps.py`) that hardcoded
AC-1's expected total for AC-2's scenario too; corrected it to derive the
expected total from the scenario's own context instead. Closed two coverage
gaps the new code left (a malformed-amount/empty-field parser branch in
`config.py`, and the CLI's unmatched-threshold-override print line) with
direct unit tests.
**Files changed:**

- `docs/REQUIREMENTS_new.md` - modified (FR-47b, FR-47e, FR-47f, FR-48c,
  FR-51c, UC13 step 4 and two new alternative flows, Definitions)
- `docs/tasks/README.md` - modified (added TASK-033 row)
- `docs/tasks/TASK-033-per-category-one-off-thresholds.md` - created
- `src/firefly_bills_analyzer/config.py` - modified
- `src/firefly_bills_analyzer/household_spend.py` - modified
- `src/firefly_bills_analyzer/exporter.py` - modified
- `src/firefly_bills_analyzer/__main__.py` - modified
- `tests/test_config.py` - modified
- `tests/test_household_spend.py` - modified
- `tests/test_exporter.py` - modified
- `tests/test_main.py` - modified
- `tests/bdd/features/TASK-033-per-category-one-off-thresholds.feature` - created
- `tests/bdd/steps/test_task_033_steps.py` - created
- `tests/bdd/steps/test_task_029_steps.py` - modified (new required
  `HouseholdSpendResult`/`OneOffPurchase` fields)
- `CHANGELOG.md` - modified

**Branch:** `git checkout task/033-per-category-one-off-thresholds`
**Stage:** `git add docs/tasks/TASK-033-per-category-one-off-thresholds.md`
**Commit:** `git commit -m "docs: record TASK-033 completion notes (TASK-033)"`
