# TASK-016 Filter transactions by source account (UC9)

## Status

done

## Requirements

**Binding:** FR-35a, FR-35b (CLI/`.env` scope only)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-002 (`fetcher.py` produces the transaction list this
module filters)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user, I want to exclude specific accounts from the analysis (e.g. a
day-to-day groceries account whose withdrawal pattern is inherently
irregular by design), or narrow the analysis to specific accounts, so that
these accounts never surface as false-positive bill candidates.

## Description

Implement `account_filter.py` — the UC9 filtering layer, modeled directly on
`category_filter.py` (TASK-006) but simpler: pure include/exclude, no
confidence weighting and no bill-naming helper.

It runs on the transaction list returned by `fetcher.py` (TASK-002), before
`analyzer.identify_recurring()` groups by payee. Since the full pipeline
already exists (TASK-002 through TASK-013 are all `done`), this task also
wires the new filter into `__main__.py`'s `main()`, immediately after the
existing `category_filter.filter_transactions()` call.

### FR-35a / FR-35b: include/exclude filtering

`account_filter.py` exposes:

```python
def filter_transactions(transactions: list[TransactionRead], config: Config) -> list[TransactionRead]
```

Matches against each transaction's `source_name` (the same field FR-30a
already resolves per pattern):

1. If `config.include_accounts` is non-empty, keep only transactions whose
   `source_name` matches the include list (FR-35a)
2. If `config.exclude_accounts` is non-empty, drop transactions whose
   `source_name` matches the exclude list (FR-35b); exclude is applied after
   include when both are configured — same ordering as
   `category_filter.filter_transactions` (FR-11a/FR-11b)
3. If neither list is configured, the function is a passthrough

Transactions with `source_name is None` never match a non-empty include or
exclude list (no accidental exclusion/inclusion of unattributed transactions).

### Config

Add to `Config` (`config.py`), following the existing `include_categories`/
`exclude_categories` pattern:

- `include_accounts: list[str]`, read from `INCLUDE_ACCOUNTS` (comma-separated,
  default empty)
- `exclude_accounts: list[str]`, read from `EXCLUDE_ACCOUNTS` (comma-separated,
  default empty)

### Wiring into `__main__.py`

In `main()`, after the existing line
`transactions = category_filter.filter_transactions(transactions, config)`,
add:

```python
transactions = account_filter.filter_transactions(transactions, config)
```

### Out of scope (deferred)

- FR-35c (web UI `GET /api/accounts` + multiselect lists): deferred until a
  web UI task exists, contingent on Open Item #5 (web framework selection),
  same status as FR-13a/FR-16/FR-30c
- `CACHE_TTL_ACCOUNTS`: only consumed by the deferred `/api/accounts`
  endpoint; not implemented here
- FR-29's CLI `--help` text update to mention `INCLUDE_ACCOUNTS`/
  `EXCLUDE_ACCOUNTS`: out of scope for this task; `--help` wording is covered
  by whichever task next touches `build_arg_parser()`

## Branch

**Branch name:** `task/016-account-filtering`
**Switch/create:** `git checkout -b task/016-account-filtering`
**Make target:** `make branch-task f=TASK-016`

## Acceptance criteria

- [x] `src/firefly_bills_analyzer/account_filter.py` exposes
      `filter_transactions(transactions, config) -> list[TransactionRead]`
- [x] When `config.include_accounts` is non-empty, only transactions whose
      `source_name` matches the include list are kept (FR-35a)
- [x] When `config.exclude_accounts` is non-empty, transactions whose
      `source_name` matches the exclude list are dropped (FR-35b); exclude is
      applied after include when both are configured
- [x] Transactions with `source_name is None` are never matched by a non-empty
      include or exclude list
- [x] When neither list is configured, `filter_transactions` is a passthrough
- [x] `Config` exposes `include_accounts: list[str]` and
      `exclude_accounts: list[str]`, read from `INCLUDE_ACCOUNTS` and
      `EXCLUDE_ACCOUNTS` (both default empty)
- [x] `__main__.py`'s `main()` calls
      `account_filter.filter_transactions(transactions, config)` after the
      existing category filter call, before `analyzer.identify_recurring()`
- [x] `tests/test_account_filter.py` uses **Hypothesis** for the
      include/exclude/passthrough combinations, mirroring
      `tests/test_category_filter.py`'s structure
- [x] `make lint && make test` pass with coverage >= baseline

## Blockers

None

## Completion

**Date:** 2026-07-20
**Summary:** Implemented `account_filter.py` mirroring `category_filter.py`'s
include/exclude structure (pure include/exclude, no confidence weighting).
Added `include_accounts`/`exclude_accounts` to `Config`, read from
`INCLUDE_ACCOUNTS`/`EXCLUDE_ACCOUNTS`. Wired
`account_filter.filter_transactions()` into `__main__.main()` right after the
existing category filter call. `tests/test_account_filter.py` covers
passthrough, include, exclude, exclude-after-include, and the
`source_name is None` non-match cases with Hypothesis. Existing `Config(...)`
call sites across the test suite (`test_analyzer.py`, `test_bills_creator.py`,
`test_fetcher.py`, `test_category_filter.py`, `benchmark_analyzer.py`) and the
`test_main.py` pipeline-wiring mocks were updated for the two new required
fields. `make lint && make test` pass (159 tests, 99% coverage); the one
`make lint` failure (MD018 in `docs/REQUIREMENTS_new.md:662`) pre-exists on
`main` and is unrelated to this task.

**Files changed:**

- `src/firefly_bills_analyzer/account_filter.py` — new (`filter_transactions()`,
  FR-35a/FR-35b)
- `tests/test_account_filter.py` — new (Hypothesis-based coverage of
  passthrough, include, exclude, exclude-after-include, and
  `source_name is None` non-match cases)
- `src/firefly_bills_analyzer/config.py` — modified (`include_accounts`/
  `exclude_accounts` fields, read from `INCLUDE_ACCOUNTS`/`EXCLUDE_ACCOUNTS`)
- `src/firefly_bills_analyzer/__main__.py` — modified (wires
  `account_filter.filter_transactions()` into `main()` after the category
  filter call)
- `tests/test_main.py` — modified (patches `account_filter.filter_transactions`
  in the pipeline-wiring test fixture; asserts it's called between fetch and
  analyze)
- `tests/test_analyzer.py` — modified (added the two new required `Config`
  fields to `_make_config()`)
- `tests/test_bills_creator.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `tests/test_fetcher.py` — modified (added the two new required `Config`
  fields to `_make_config()`)
- `tests/test_category_filter.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `tests/benchmark_analyzer.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `CHANGELOG.md` — modified (Unreleased entry for `INCLUDE_ACCOUNTS`/
  `EXCLUDE_ACCOUNTS`)
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-016-account-filtering.md` — this file

**Branch:** `git checkout task/016-account-filtering`
**Stage:** `git add src/firefly_bills_analyzer/account_filter.py tests/test_account_filter.py src/firefly_bills_analyzer/config.py src/firefly_bills_analyzer/__main__.py tests/test_main.py tests/test_analyzer.py tests/test_bills_creator.py tests/test_fetcher.py tests/test_category_filter.py tests/benchmark_analyzer.py CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-016-account-filtering.md`
**Commit:** `git commit -m "feat: add account filtering functionality (UC9) with INCLUDE_ACCOUNTS/EXCLUDE_ACCOUNTS support"`
