# TASK-022 Align category resolution scope with amount clusters and define tie-breaking (FR-13b)

## Status

done

## Requirements

**Binding:** FR-13b
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-008 (category-aware bill naming, which implemented the
original payee-wide FR-13b), TASK-012 and TASK-014 (which introduced the amount
cluster as the unit a bill is named from)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user whose water utility bills three separate charges under one merchant
name, I want each resulting bill to be named from its own charge's category
rather than from a majority computed across all three, so that the bill names
describe what they actually are.

## Description

FR-13b as written before v0.2.23 required the category majority share to be
computed "over all of the payee's transactions". `_build_pattern()` calls
`resolve_category_name(cluster, config)` and therefore computes it over the
amount cluster. The two have diverged since TASK-012/TASK-014 introduced
clustering, and nothing detected the divergence because no test exercises a
payee whose clusters have different category profiles.

Verified divergence, one source account, two corroborated amount clusters:

| Cluster | Cluster-scoped result (code) | Payee-scoped result (FR-13b as written) |
| ------- | ---------------------------- | --------------------------------------- |
| mean 100, all category `Vatten` | `Vatten` | `None` (50/50 payee-wide, threshold 0.80) |
| mean 1000, all category `Sophantering` | `Sophantering` | `None` (same) |

The code's behavior is the correct one: FR-32c already disambiguates bill names
per cluster, so the naming unit is the cluster, and a payee-wide majority would
strip the category name from exactly the multi-charge payees that need it most.
The requirement was stale, not the implementation. FR-13b is revised in
`docs/REQUIREMENTS_new.md` v0.2.23 to specify the cluster scope.

This task therefore adds no behavior for the scope part. It locks the corrected
scope down with the tests that were missing, and fixes the two things that are
genuinely wrong in the code.

### Change 1: tie-breaking (behavioral)

The `resolve_category_name()` helper returns the first entry of `counts.most_common(1)`. On a tie between two
or more equally frequent categories, `Counter.most_common` breaks the tie by
first-insertion order, which is the order transactions arrived from the Firefly
III API. The resolved bill name is therefore not a function of the data alone,
and a re-fetch can rename a bill.

Revised FR-13b requires no category name when two or more categories are tied
for most frequent, regardless of `CATEGORY_MAJORITY_THRESHOLD`. Note this only
changes behavior when the threshold is configured below 0.50; at the 0.80
default a tie cannot reach the threshold anyway. Implement it as an explicit
tie check rather than relying on that arithmetic, so the behavior does not
depend on the configured threshold.

### Change 2: parameter name (non-behavioral)

`resolve_category_name(transactions_for_payee, config)` no longer receives a
payee's transactions. Rename the parameter to `transactions_for_cluster` and
update the docstring to state the cluster scope and the tie rule. The
misleading name is what let the divergence sit unnoticed.

## Branch

**Branch name:** `task/022-category-scope-and-tiebreak`
**Switch/create:** `git checkout -b task/022-category-scope-and-tiebreak`
**Make target:** `make branch-task f=TASK-022`

## Acceptance criteria (Gherkin)

- [x] Scenario: Each amount cluster of a multi-charge payee resolves its own category name
      Given one payee and one source account, whose transactions form two corroborated amount clusters, the smaller cluster entirely in category `Vatten` and the larger entirely in category `Sophantering`
      When `identify_recurring()` builds the patterns
      Then the smaller cluster's pattern resolves category `Vatten` and the larger cluster's pattern resolves category `Sophantering`, rather than both resolving `None` from a payee-wide 50/50 share

- [x] Scenario: The majority share is measured against the cluster, not the payee
      Given a payee whose transactions are 90% category `El` overall, but one of whose amount clusters is entirely category `Nat`
      When `identify_recurring()` builds the patterns
      Then that cluster's pattern resolves category `Nat`

- [x] Scenario: A tie resolves to no category name
      Given an amount cluster with an equal number of transactions in two different categories and `CATEGORY_MAJORITY_THRESHOLD` set to 0.40
      When the category name is resolved
      Then no category name is resolved, even though each category's share exceeds the threshold

- [x] Scenario: A tie resolves identically regardless of transaction order
      Given the same tied cluster with its transactions in reverse order
      When the category name is resolved
      Then the result is the same as for the original order

- [x] Scenario: An outright majority is unaffected by the tie rule
      Given a cluster where one category holds a share at or above `CATEGORY_MAJORITY_THRESHOLD` and no other category matches its count
      When the category name is resolved
      Then that category name is resolved, as before

- [x] `resolve_category_name`'s first parameter is named `transactions_for_cluster`, and its docstring states the cluster scope and the tie rule

- [x] Hypothesis property test: the resolved category name is invariant under any permutation of the input transactions

- [x] All existing `tests/test_category_filter.py` and `tests/test_analyzer.py` category-naming tests pass; any that assert payee-wide scope are shown to be untouched by this change, or are corrected with the reason recorded in the Completion summary

- [x] `make lint && make test` pass with coverage >= the TASK-018 baseline

## Out of scope

- FR-12's confidence boost condition, and FR-27's penalty condition. The penalty
  interaction with unresolved category names is a separate defect handled by
  TASK-023; this task must not change `_confidence()`
- `CATEGORY_MAJORITY_THRESHOLD`'s default value or its semantics
- FR-11a/FR-11b filtering, which operates per transaction before grouping and is
  unaffected by cluster scope
- Bill-name disambiguation (FR-32c), which already operates per cluster

## Blockers

None

## Completion

**Date:** 2026-08-03
**Summary:** The cluster-scoped naming behavior itself was already correct
(implemented by TASK-012/TASK-014's `_build_pattern()`, which calls
`resolve_category_name(cluster, config)`) but had no test distinguishing it
from the payee-wide scope FR-13b used to require, so the divergence had sat
unnoticed. Added `test_each_amount_cluster_resolves_its_own_category_name`
and `test_category_majority_measured_against_cluster_not_payee` to
`tests/test_analyzer.py`, both exercising `identify_recurring()` end-to-end
with a payee whose two corroborated amount clusters carry different
category profiles. Implemented the one genuine behavior change: an explicit
tie check in `resolve_category_name()` (`src/firefly_bills_analyzer/category_filter.py`)
that returns `None` whenever two or more categories are tied for most
frequent in a cluster, regardless of `CATEGORY_MAJORITY_THRESHOLD`, instead
of relying on `Counter.most_common(1)` silently breaking ties by
first-insertion (i.e. Firefly III API fetch) order. Renamed the function's
first parameter from `transactions_for_payee` to `transactions_for_cluster`
and rewrote its docstring to state the cluster scope and the tie rule; the
call site in `analyzer.py` passes positionally and needed no change. Added
four tests to `tests/test_category_filter.py`: a tie-resolves-to-`None`
case, an order-invariance check on the same tied cluster reversed, an
outright-majority case confirming the tie rule leaves non-tied results
unaffected, and a Hypothesis property test asserting the resolved category
name is invariant under any permutation of the input transactions. No
existing test asserted payee-wide scope, so none needed correcting. All 199
pre-existing tests plus 6 new ones (205 total, plus the Hypothesis property
tests which each run multiple examples) pass; `make lint` and `make test`
are green with coverage unchanged at 99% (matches the TASK-018/TASK-021-era
baseline).
**Files changed:**

- `src/firefly_bills_analyzer/category_filter.py` — modified (tie-break rule,
  parameter rename, docstring)
- `tests/test_category_filter.py` — modified (tie-break and permutation
  invariance tests)
- `tests/test_analyzer.py` — modified (cluster-scope regression tests via
  `identify_recurring()`)
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-022-category-scope-and-tiebreak.md` — this file

`docs/REQUIREMENTS_new.md` was not touched on this branch: FR-13b/FR-13c's
revision to v0.2.23 (cluster scope and the tie rule) had already landed on
`main` ahead of this task, per the task description's "Spec side is already
done" note.

**Branch:** `git checkout task/022-category-scope-and-tiebreak`
**Stage:** `git add src/firefly_bills_analyzer/category_filter.py tests/test_category_filter.py tests/test_analyzer.py CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-022-category-scope-and-tiebreak.md`
**Commit:** `git commit -m "fix: resolve bill category names per amount cluster and drop the name on a tied category count (FR-13b)"`
