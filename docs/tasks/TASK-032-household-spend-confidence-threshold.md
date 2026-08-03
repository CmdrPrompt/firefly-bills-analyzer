# TASK-032 Household spend excludes only high-confidence recurring patterns (FR-48b, UC13)

## Status

todo

## Requirements

**Binding:** FR-48b, UC13, FR-04a
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-028 (household spend aggregation) and TASK-003 (recurring pattern identification)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user with groceries, utilities, and other household costs bought across
multiple transactions that UC2 cannot reliably cluster, I want those real
ongoing costs measured as household spend rather than silently excluded
because they belong to a low-confidence pattern, so that my actual cash flow
is visible in the export.

## Description

Currently, `pattern_member_transactions()` returns every transaction belonging
to any qualifying recurring cluster (>= min_occurrences), with no confidence
check. This causes FR-48b to exclude low-confidence patterns wholesale,
silencing real household costs.

The fix: `pattern_member_transactions()` must compute each cluster's
confidence using the same path `identify_recurring()` uses (`_build_pattern`
/ `_confidence`), and only include a cluster's transactions when that
confidence is >= `config.high_confidence_threshold` (FR-04a, default 0.80).

A withdrawal in a pattern below the threshold will then remain eligible for
household spend measurement under UC13 step 3, as specified in UC13's
alternative flow.

This unblocks the real-world scenario where a single account/payee combination
has many varying amounts with no corroborated same-date co-occurrence: UC2's
clustering yields one low-confidence "irregular" cluster that matches UC13's
category filter, and that household cost is now correctly measured instead of
silently dropped.

## Branch

**Branch name:** `task/032-household-spend-confidence-threshold`
**Switch/create:** `git checkout -b task/032-household-spend-confidence-threshold`
**Make target:** `make branch-task f=TASK-032`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature

- [ ] 1. Scenario: A withdrawal in a high-confidence pattern is excluded from household spend
      See tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature: Scenario "High-confidence recurring pattern excludes withdrawal from household spend"

- [ ] 2. Scenario: A withdrawal in a low-confidence pattern is included in household spend
      See tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature: Scenario "Low-confidence pattern allows withdrawal into household spend"

- [ ] 3. Scenario: The ICA regression scenario (many transactions, varying amounts, no same-day co-occurrence, low confidence) is measured as household spend
      See tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature: Scenario "Large single-cluster payee with varying amounts is measured as household spend"

- [ ] 4. `make lint && make test && make bdd` pass with coverage >= the TASK-031 baseline

## Out of scope

- Changing `_build_pattern()`, `_confidence()`, or the confidence calculation itself
- Changing `MIN_OCCURRENCES` or clustering behavior
- Modifying `identify_recurring()` or its acceptance criteria
- Altering the definition of `HIGH_CONFIDENCE_THRESHOLD` beyond reading it from config

## Blockers

None

## Completion

**Date:** 2026-08-03
**Summary:** `pattern_member_transactions()` now computes each qualifying cluster's
confidence via `_build_pattern()` (same path `identify_recurring()` uses) and
only includes a cluster's transactions when confidence >=
`config.high_confidence_threshold`. Low-confidence clusters no longer have
their transactions silently excluded from household spend.
**Files changed:**

- `docs/REQUIREMENTS_new.md` - modified (FR-48b, FR-04a trace, UC13 step 3 and alternative flow)
- `docs/tasks/README.md` - modified (added TASK-032 row)
- `docs/tasks/TASK-032-household-spend-confidence-threshold.md` - created
- `src/firefly_bills_analyzer/analyzer.py` - modified
- `tests/test_analyzer.py` - modified
- `tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature` - created
- `tests/bdd/steps/test_task_032_steps.py` - created
- `CHANGELOG.md` - modified

**Branch:** `git checkout task/032-household-spend-confidence-threshold`
**Stage:** `git add docs/REQUIREMENTS_new.md docs/tasks/README.md docs/tasks/TASK-032-household-spend-confidence-threshold.md src/firefly_bills_analyzer/analyzer.py tests/test_analyzer.py tests/bdd/features/TASK-032-household-spend-confidence-threshold.feature tests/bdd/steps/test_task_032_steps.py CHANGELOG.md`
**Commit:** `git commit -m "fix: household spend no longer excludes low-confidence recurring patterns (FR-48b, TASK-032)"`
**Commit:** feat: only exclude high-confidence recurring patterns from household spend (TASK-032)
