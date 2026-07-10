# TASK-006 Filter transactions by category (UC6)

## Status

done

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

**Open Item #7 resolved (spec v0.2.6):** FR-13b now uses majority/mode-based
tolerance, not a strict "exactly one distinct category" reading. A category is
included in the bill name when it accounts for at least
`CATEGORY_MAJORITY_THRESHOLD` (default `0.80`) of a payee's transactions,
counting uncategorized transactions as their own non-matching bucket. See
`docs/REQUIREMENTS_new.md` Changelog 0.2.6.

Covers UC6, FR-11a, FR-11b, FR-14.

## Branch

**Branch name:** `task/006-category-filtering`
**Switch/create:** `git checkout -b task/006-category-filtering`
**Make target:** `make branch-task f=TASK-006`

## Acceptance criteria

- [x] `src/firefly_bills_analyzer/category_filter.py` exposes
      `filter_transactions(transactions, config) -> list[TransactionRead]`
- [x] When `config.include_categories` is non-empty, only transactions whose
      category matches the include list are kept (FR-11a)
- [x] When `config.exclude_categories` is non-empty, transactions whose category
      matches the exclude list are dropped (FR-11b); exclude is applied after
      include when both are configured
- [x] Uncategorized transactions are kept unconditionally when
      `config.uncategorized_behavior` is `"include"` or `"neutral"`, and
      dropped when it is `"exclude"` (FR-14). `"include"` and `"neutral"`
      are filtering-equivalent here — `"neutral"` only differs downstream in
      TASK-003's confidence scoring (`UNCATEGORIZED_CONFIDENCE_PENALTY`, FR-27),
      not in this module
- [x] `category_filter.py` also exposes
      `resolve_category_name(transactions_for_payee, config) -> str | None`,
      returning the category name that accounts for at least
      `config.category_majority_threshold` of the payee's transactions (else
      `None`); uncategorized transactions count as their own non-matching
      bucket (FR-13b, spec v0.2.6); not yet consumed by any other module
      (that wiring is TASK-008, once `bills_creator.py` exists)
- [x] `Config` exposes `category_majority_threshold: float`, read from
      `CATEGORY_MAJORITY_THRESHOLD` (default `0.80`)
- [x] `tests/test_category_filter.py` uses **Hypothesis** for the
      include/exclude/uncategorized combinations and for
      `resolve_category_name`; additionally covers the "no filters configured"
      passthrough case (UC6: "If no categories are selected, the analysis runs
      without filtering or weighting")
- [x] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:** 2026-07-11
**Summary:** Implemented `category_filter.filter_transactions` (FR-11a/b
include/exclude filtering, FR-14 uncategorized handling) and
`resolve_category_name` (FR-13b, majority/mode-based tolerance per spec v0.2.6,
resolved with the user before implementation — Open Item #7). Added
`Config.category_majority_threshold` (`CATEGORY_MAJORITY_THRESHOLD`, default
`0.80`). Tests use Hypothesis for the filter/resolve property space plus
explicit examples for the threshold edge cases. TASK-002 was merged to `main`
first (PR #2) since TASK-006 depends on it and stacking branches was not
wanted.
**Files changed:**

- `src/firefly_bills_analyzer/category_filter.py` — created
- `tests/test_category_filter.py` — created
- `src/firefly_bills_analyzer/config.py` — modified (`category_majority_threshold`)
- `tests/test_config.py` — modified
- `tests/test_fetcher.py` — modified (`_make_config` helper updated for new field)
- `pyproject.toml` — modified (`hypothesis` dev dependency)
- `uv.lock` — modified
- `docs/REQUIREMENTS_new.md` — modified (FR-13b majority threshold, v0.2.6)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-006-category-filtering.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/006-category-filtering`
**Stage:** `git add src/firefly_bills_analyzer/category_filter.py tests/test_category_filter.py src/firefly_bills_analyzer/config.py tests/test_config.py tests/test_fetcher.py pyproject.toml uv.lock docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/TASK-006-category-filtering.md docs/tasks/README.md`
**Commit:** `git commit -m "Add category_filter.py for UC6 include/exclude filtering (TASK-006)"`
