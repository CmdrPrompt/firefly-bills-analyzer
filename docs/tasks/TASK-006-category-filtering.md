# TASK-006 Filter transactions by category (UC6)

## Status

todo

## Description

Implement `category_filter.py` — the UC6 filtering layer named in the
Architecture section of the spec but not yet covered by any task. It runs on
the transaction list returned by `fetcher.py` (TASK-002), before the
transactions are grouped by `analyzer.py` (TASK-003).

This task covers include/exclude filtering by category (FR-11a, FR-11b) and
the configured handling of uncategorized transactions (FR-14). It also
exposes the `resolve_category_name` helper used later by TASK-008 for
bill naming (FR-13b) — the helper is written and tested here, but not yet
wired into bill creation, since `bills_creator.py` does not exist until
TASK-004.

The category confidence boost itself (FR-12) is already covered by TASK-003
and is out of scope here — TASK-003 reads `category_name` on the filtered
transactions and applies the boost when it is in `config.include_categories`.

**Depends on:** TASK-002 (`fetcher.py` produces the transaction list this
module filters). Implement this task immediately after TASK-002 and before
TASK-003, so `analyzer.py` is written against the already-filtered
transaction list instead of being retrofitted later.

**⚠ Before implementing `resolve_category_name`:** confirm Open Item #7 with
the user first. "Exactly one distinct category" is currently interpreted
strictly — a single differently-categorized transaction among the payee's
history makes `resolve_category_name` return `None` (no category in the bill
name). The user was still weighing this against a majority/mode-based
tolerance as of the last discussion — do not assume the strict reading still
holds without asking again at implementation time.

Covers UC6, FR-11a, FR-11b, FR-14.

## Branch

**Branch name:** `task/006-category-filtering`
**Switch/create:** `git checkout -b task/006-category-filtering`
**Make target:** `make branch-task f=TASK-006`

## Acceptance criteria

- [ ] `src/firefly_bills_analyzer/category_filter.py` exposes
      `filter_transactions(transactions, config) -> list[TransactionRead]`
- [ ] When `config.include_categories` is non-empty, only transactions whose
      category matches the include list are kept (FR-11a)
- [ ] When `config.exclude_categories` is non-empty, transactions whose category
      matches the exclude list are dropped (FR-11b); exclude is applied after
      include when both are configured
- [ ] Uncategorized transactions are kept unconditionally when
      `config.uncategorized_behavior` is `"include"` or `"neutral"`, and
      dropped when it is `"exclude"` (FR-14). `"include"` and `"neutral"`
      are filtering-equivalent here — `"neutral"` only differs downstream in
      TASK-003's confidence scoring (`UNCATEGORIZED_CONFIDENCE_PENALTY`, FR-27),
      not in this module
- [ ] `category_filter.py` also exposes
      `resolve_category_name(transactions_for_payee) -> str | None`, returning
      the category name only when exactly one distinct category occurs among
      the payee's transactions, else `None`; not yet consumed by any other
      module (that wiring is TASK-008, once `bills_creator.py` exists)
- [ ] `tests/test_category_filter.py` uses **Hypothesis** for the
      include/exclude/uncategorized combinations and for
      `resolve_category_name`; additionally covers the "no filters configured"
      passthrough case (UC6: "If no categories are selected, the analysis runs
      without filtering or weighting")
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/category_filter.py` — created
- `tests/test_category_filter.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-006-category-filtering.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/006-category-filtering`
**Stage:** `git add src/firefly_bills_analyzer/category_filter.py tests/test_category_filter.py CHANGELOG.md docs/tasks/TASK-006-category-filtering.md`
**Commit:** `git commit -m "Add category_filter.py for UC6 include/exclude filtering (TASK-006)"`
