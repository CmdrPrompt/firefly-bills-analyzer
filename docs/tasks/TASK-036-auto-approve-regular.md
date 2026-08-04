# TASK-036 Add --auto-approve-regular CLI flag for non-irregular patterns

## Status
todo

## Requirements
**Binding:** FR-03, FR-04a, FR-04c, UC3 (lines 233-240)
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-005
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a cash-flow analyst, I want to auto-approve only regular recurring bills (monthly, quarterly, half-yearly, yearly) when their confidence is high, so that irregular expenses are brought to my attention for verification rather than silently skipped or auto-rejected.

## Description
Add a new CLI flag `--auto-approve-regular` (mutually exclusive with the existing `--auto-approve`) that implements a more conservative auto-approval strategy in terminal review mode (UC3).

The existing `--auto-approve` flag approves all patterns at or above the confidence threshold and silently skips the rest. The new `--auto-approve-regular` flag introduces a two-gate approval: patterns must have both (1) a non-irregular frequency (monthly, quarterly, half-yearly, or yearly per FR-03) AND (2) confidence at or above the threshold (FR-04a) to be auto-approved. Every other pattern—whether irregular frequency (regardless of confidence) or non-irregular but below-threshold confidence—is presented for interactive y/n/a/q review, not skipped.

This allows users with recurring irregular expenses to be prompted on those items while still automating approval of predictable recurring charges.

**Implementation requirements:**
- `src/firefly_bills_analyzer/__main__.py`: `build_arg_parser()` shall add `--auto-approve-regular` as a new flag in a mutually exclusive group with `--auto-approve` using argparse's `add_mutually_exclusive_group()`. Passing both flags together shall produce an argparse error (standard behavior of `add_mutually_exclusive_group()`).
- `_review()` function shall support the new `--auto-approve-regular` mode: patterns with frequency != "irregular" AND confidence >= threshold are auto-approved (printed as `[auto] approved: ...`); all other patterns fall through to the same interactive y/n/a/q prompt loop already used by the manual (neither flag) review path.
- `main()` function threads the new flag into `_review()`, treating it as a variant of the auto-approval mode.
- `RecurringPattern.frequency` already carries the classification from FR-03, so no analyzer module change is needed.

## Branch
**Branch name:** `task/036-auto-approve-regular`
**Switch/create:** `git checkout -b task/036-auto-approve-regular`
**Make target:** `make branch-task f=TASK-036`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-036-auto-approve-regular.feature

- [ ] 1. Non-irregular, high-confidence pattern is auto-approved under --auto-approve-regular
      See tests/bdd/features/TASK-036-auto-approve-regular.feature: Scenario "Monthly pattern above confidence threshold is auto-approved"

- [ ] 2. Irregular pattern is presented for interactive review, not skipped
      See tests/bdd/features/TASK-036-auto-approve-regular.feature: Scenario "Irregular pattern is presented for interactive review"

- [ ] 3. Non-irregular pattern below confidence threshold is presented for interactive review, not skipped
      See tests/bdd/features/TASK-036-auto-approve-regular.feature: Scenario "Quarterly pattern below confidence threshold is presented for interactive review"

- [ ] 4. Existing --auto-approve behavior is unaffected
      See tests/bdd/features/TASK-036-auto-approve-regular.feature: Scenario "Existing --auto-approve flag still auto-approves and skips below-threshold entries"

- [ ] 5. Passing both --auto-approve and --auto-approve-regular produces an argparse error
      See tests/bdd/features/TASK-036-auto-approve-regular.feature: Scenario "Both flags together produce mutual exclusivity error"

## Out of scope
- Web UI support for the new flag (contingent on Open Item #5)

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `src/firefly_bills_analyzer/__main__.py` - created / modified
- `tests/test_main.py` - modified
- `tests/bdd/features/TASK-036-auto-approve-regular.feature` - created
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/036-auto-approve-regular`
**Stage:** `src/firefly_bills_analyzer/__main__.py tests/test_main.py tests/bdd/features/TASK-036-auto-approve-regular.feature CHANGELOG.md`
**Commit:** `Add --auto-approve-regular CLI flag for non-irregular high-confidence patterns`
