# TASK-023 Stop penalizing fully categorized patterns that resolve no category name (FR-13c, FR-27)

## Status

todo

## Requirements

**Binding:** FR-13c, FR-27
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-022 (establishes the cluster as the scope over which
category presence is judged, and renames the resolution helper's parameter
accordingly)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user who has categorized every transaction for a payee, I want that
payee's suggestions ranked on the strength of their recurrence pattern, not
demoted for a naming outcome, so that a real bill I categorized under two
related categories is not pushed below the auto-approval threshold.

## Description

`_confidence()` applies `UNCATEGORIZED_CONFIDENCE_PENALTY` when
`category_name is None`. But `category_name` is FR-13b's *naming* result, and
it is `None` in two structurally different situations:

1. No transaction in the cluster carries a category. The pattern really is
   uncategorized, and the penalty is what FR-14 and the "Neutral" definition
   intend.
2. Every transaction carries a category, but no single category reaches
   `CATEGORY_MAJORITY_THRESHOLD`. FR-13b correctly declines to put a name in
   the bill title. Nothing about the data is unknown.

Case 2 is penalized today, which is wrong. The user categorized the data; the
absent name is a bill-naming outcome, not a data-quality signal.

Verified against the current code with `UNCATEGORIZED_BEHAVIOR=neutral`,
`UNCATEGORIZED_CONFIDENCE_PENALTY=0.10`, `CATEGORY_MAJORITY_THRESHOLD=0.80`,
twelve monthly transactions of an identical amount:

| Cluster | Resolved name | Confidence |
| ------- | ------------- | ---------- |
| all transactions in category `El` | `El` | 0.989 |
| 60% `El`, 40% `Hushall`, none uncategorized | `None` | 0.889 |

The 0.100 gap is the penalty, applied to a cluster with no uncategorized
transaction in it. With `HIGH_CONFIDENCE_THRESHOLD` at its 0.80 default the
effect is invisible on a strong pattern like this one, but on a pattern near
the cutoff it is the difference between auto-approval and manual review, and
the reason is not surfaced anywhere in the output.

FR-27 is revised in `docs/REQUIREMENTS_new.md` v0.2.23 to scope the penalty to
uncategorized patterns (new definition), and FR-13c states the exemption.

### Change

In `analyzer.py`, `_build_pattern()` currently passes only `category_name` into
`_confidence()`. That is insufficient to distinguish the two cases. Pass an
additional flag derived from the cluster — whether any transaction in it carries
a category name — and gate the penalty on the absence of that, not on the
absence of a resolved name.

Keep the derivation in one place. A small helper next to
`resolve_category_name()` in `category_filter.py` is the natural home, since
both answer questions about a cluster's categories, and putting it there keeps
`_confidence()`'s signature honest about what it needs.

FR-12's boost is unchanged: it still keys off the resolved category name being
in the include list.

## Branch

**Branch name:** `task/023-uncategorized-penalty-misapplied`
**Switch/create:** `git checkout -b task/023-uncategorized-penalty-misapplied`
**Make target:** `make branch-task f=TASK-023`

## Acceptance criteria (Gherkin)

- [ ] Scenario: A fully categorized cluster with no majority is not penalized
      Given a cluster whose transactions all carry a category name, split 60/40 across two categories, with `UNCATEGORIZED_BEHAVIOR` set to `neutral`
      When the confidence score is computed
      Then `UNCATEGORIZED_CONFIDENCE_PENALTY` is not subtracted, and the score equals that of an otherwise identical single-category cluster minus only its category boost difference

- [ ] Scenario: A cluster with no categories at all is still penalized
      Given a cluster in which no transaction carries a category name, with `UNCATEGORIZED_BEHAVIOR` set to `neutral`
      When the confidence score is computed
      Then `UNCATEGORIZED_CONFIDENCE_PENALTY` is subtracted, as before

- [ ] Scenario: A partially categorized cluster is treated as categorized
      Given a cluster in which at least one transaction carries a category name and at least one does not, with `UNCATEGORIZED_BEHAVIOR` set to `neutral`
      When the confidence score is computed
      Then `UNCATEGORIZED_CONFIDENCE_PENALTY` is not subtracted, per the "Uncategorized pattern" definition

- [ ] Scenario: The penalty remains off outside neutral behavior
      Given an uncategorized cluster with `UNCATEGORIZED_BEHAVIOR` set to `include`
      When the confidence score is computed
      Then no penalty is subtracted, as before

- [ ] Scenario: The category boost is unaffected
      Given a cluster resolving a category name that appears in `INCLUDE_CATEGORIES`
      When the confidence score is computed
      Then `CATEGORY_CONFIDENCE_BOOST` is added exactly as before this change (FR-12)

- [ ] The regression is captured as a named test reproducing the measured case: twelve equal monthly transactions split 60/40 across two categories score the same as the single-category equivalent apart from the boost, rather than 0.100 lower

- [ ] Hypothesis property test: for any cluster containing at least one categorized transaction, the computed confidence is independent of `UNCATEGORIZED_CONFIDENCE_PENALTY`

- [ ] `make lint && make test` pass with coverage >= the TASK-018 baseline

## Out of scope

- FR-13b's resolution scope and tie rule, owned by TASK-022
- The value or default of `UNCATEGORIZED_CONFIDENCE_PENALTY`, and the three
  `UNCATEGORIZED_BEHAVIOR` modes
- FR-11a/FR-11b/FR-14 filtering behavior for uncategorized transactions
- Surfacing the reason for a penalty in the CLI review line. Worth doing, but it
  is an output change and belongs to whichever task next touches
  `_format_suggestion()`
- Re-scoring or re-reporting any bill already created in Firefly III

## Blockers

None

## Completion

**Date:** YYYY-MM-DD
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/analyzer.py` — modified
- `src/firefly_bills_analyzer/category_filter.py` — modified
- `tests/test_analyzer.py` — modified
- `tests/test_category_filter.py` — modified
- `docs/REQUIREMENTS_new.md` — modified prior to implementation (v0.2.22 → v0.2.23)
- `CHANGELOG.md` — modified
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-023-uncategorized-penalty-misapplied.md` — this file

**Branch:** `git checkout task/023-uncategorized-penalty-misapplied`
**Stage:** `git add src/firefly_bills_analyzer/analyzer.py src/firefly_bills_analyzer/category_filter.py tests/test_analyzer.py tests/test_category_filter.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-023-uncategorized-penalty-misapplied.md`
**Commit:** `git commit -m "fix: apply the uncategorized confidence penalty only to patterns with no categorized transactions (FR-13c)"`
