# TASK-008 Include category name in bill name (UC6)

## Status

todo

## Description

Wire `category_filter.resolve_category_name` (TASK-006) into
`bills_creator.py` (TASK-004) so that when exactly one category occurs among
a payee's transactions, the bill name includes that category name, per FR-13b.

This is split out from TASK-006 because it touches `bills_creator.py`, which
does not exist until TASK-004 completes, and from TASK-004 itself to keep
that task focused on the core create/duplicate-check/dry-run flow.

**Depends on:** TASK-004 (`bills_creator.py` must exist) and TASK-006
(`resolve_category_name` must exist). Implement immediately after TASK-004.

**⚠ Open Item #7 (spec):** this task consumes whatever interpretation of
"exactly one category" TASK-006 shipped with. If TASK-006 confirmed the
strict reading (default assumption) this task needs no changes; if a
majority/mode-based tolerance was chosen instead, the "no-category" and
"multi-category unchanged" test cases below must be re-checked against that
looser rule before marking this task done.

Covers UC6, FR-13b.

## Branch

**Branch name:** `task/008-category-aware-bill-naming`
**Switch/create:** `git checkout -b task/008-category-aware-bill-naming`
**Make target:** `make branch-task f=TASK-008`

## Acceptance criteria

- [ ] `bills_creator.create_bills` calls
      `category_filter.resolve_category_name` per payee and, when it returns a
      value, appends it to the bill name (e.g. `"{payee} ({category})"`)
- [ ] When `resolve_category_name` returns `None` (no category, or more than
      one distinct category among the payee's transactions), the bill name is
      the payee name unchanged — existing TASK-004 tests continue to pass
      without modification
- [ ] Duplicate-bill matching (FR-05) compares against the final,
      category-aware name
- [ ] `tests/test_bills_creator.py` gains cases for: single-category payee
      (name includes category), no-category payee (name unchanged),
      multi-category payee (name unchanged)
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/bills_creator.py` — modified (category-aware naming)
- `tests/test_bills_creator.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-008-category-aware-bill-naming.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/008-category-aware-bill-naming`
**Stage:** `git add src/firefly_bills_analyzer/bills_creator.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-008-category-aware-bill-naming.md`
**Commit:** `git commit -m "Include category name in bill naming per FR-13b (TASK-008)"`
