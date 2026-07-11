# TASK-008 Include category name in bill name (UC6)

## Status

done

## Description

Use `RecurringPattern.category_name` (already populated by
`category_filter.resolve_category_name` inside `analyzer.py`, TASK-003/006)
in `bills_creator.py` (TASK-004) so that when a category is resolved for a
payee, the bill name includes that category name, per FR-13b.

**Implementation note:** `resolve_category_name` is not called again inside
`bills_creator.py`. `RecurringPattern` already carries the resolved
`category_name` field (set in `analyzer.py` using the same majority-threshold
logic), so `create_bills` simply reads `pattern.category_name` — no new
dependency on `category_filter` or raw per-payee transaction lists is
introduced. Confirmed with the user on 2026-07-11.

This is split out from TASK-006 because it touches `bills_creator.py`, which
does not exist until TASK-004 completes, and from TASK-004 itself to keep
that task focused on the core create/duplicate-check/dry-run flow.

**Depends on:** TASK-004 (`bills_creator.py` must exist) and TASK-006
(`RecurringPattern.category_name` must exist). Implement immediately after
TASK-004.

**Open Item #7 (spec):** already resolved in spec v0.2.6 — FR-13b uses a
majority/mode-based tolerance (`CATEGORY_MAJORITY_THRESHOLD`). The
"no-category" and "multi-category unchanged" test cases below map to "no
majority category" under that rule, which `resolve_category_name` already
enforces before `analyzer.py` sets `category_name`; no further check needed.

Covers UC6, FR-13b.

## Branch

**Branch name:** `task/008-category-aware-bill-naming`
**Switch/create:** `git checkout -b task/008-category-aware-bill-naming`
**Make target:** `make branch-task f=TASK-008`

## Acceptance criteria

- [x] `bills_creator.create_bills` reads `pattern.category_name` per payee
      and, when it is not `None`, appends it to the bill name (e.g.
      `"{payee} ({category})"`)
- [x] When `pattern.category_name` is `None` (no category, or no majority
      category among the payee's transactions per FR-13b), the bill name is
      the payee name unchanged — existing TASK-004 tests continue to pass
      without modification
- [x] Duplicate-bill matching (FR-05) compares against the final,
      category-aware name
- [x] `tests/test_bills_creator.py` gains cases for: single-category payee
      (name includes category), no-category payee (name unchanged),
      multi-category payee (name unchanged)
- [x] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:** 2026-07-11
**Summary:** `bills_creator._bill_name` appends the payee's resolved
`pattern.category_name` (already computed by `analyzer.py` via
`resolve_category_name`, FR-13b) to the bill name when present, e.g.
`"Netflix (Subscriptions)"`. Duplicate detection uses this final name.
Extracted into a helper to keep `create_bills`'s cyclomatic complexity
within the `complexipy` threshold.
**Files changed:**

- `src/firefly_bills_analyzer/bills_creator.py` — modified (category-aware naming)
- `tests/test_bills_creator.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-008-category-aware-bill-naming.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/008-category-aware-bill-naming`
**Stage:** `git add src/firefly_bills_analyzer/bills_creator.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-008-category-aware-bill-naming.md`
**Commit:** `git commit -m "Include category name in bill naming per FR-13b (TASK-008)"`
