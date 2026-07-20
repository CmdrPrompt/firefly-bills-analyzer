# TASK-017 Filter transactions by payee / destination account (UC10)

## Status

done

## Requirements

**Binding:** FR-36a, FR-36b (CLI/`.env` scope only)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-002 (`fetcher.py` produces the transaction list this
module filters)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user, I want to exclude specific payees from the analysis (e.g. a "Cash
account" destination representing cash withdrawals, whose spending pattern is
inherently irregular by design), or narrow the analysis to specific payees, so
that these payees never surface as false-positive bill candidates.

## Description

Implement `payee_filter.py` — the UC10 filtering layer, modeled directly on
`account_filter.py` (TASK-016): pure include/exclude, no confidence weighting
and no bill-naming helper. The only difference from `account_filter.py` is the
matched field: `destination_name` instead of `source_name`.

It runs on the transaction list returned by `fetcher.py` (TASK-002), before
`analyzer.identify_recurring()` groups by payee. Since the full pipeline
already exists (TASK-002 through TASK-013 are all `done`), this task also
wires the new filter into `__main__.py`'s `main()`, immediately after the
existing account filter call (or the category filter call if TASK-016 has not
yet been merged when this task is implemented — check `__main__.py`'s current
state and place it after whichever filter call runs last).

### FR-36a / FR-36b: include/exclude filtering

`payee_filter.py` exposes:

```python
def filter_transactions(transactions: list[TransactionRead], config: Config) -> list[TransactionRead]
```

Matches against each transaction's `destination_name` (the same field UC2
step 1 already groups by):

1. If `config.include_payees` is non-empty, keep only transactions whose
   `destination_name` matches the include list (FR-36a)
2. If `config.exclude_payees` is non-empty, drop transactions whose
   `destination_name` matches the exclude list (FR-36b); exclude is applied
   after include when both are configured — same ordering as
   `account_filter.filter_transactions` (FR-35a/FR-35b) and
   `category_filter.filter_transactions` (FR-11a/FR-11b)
3. If neither list is configured, the function is a passthrough

Transactions with `destination_name is None` never match a non-empty include
or exclude list (no accidental exclusion/inclusion of unattributed
transactions).

### Config

Add to `Config` (`config.py`), following the existing `include_accounts`/
`exclude_accounts` pattern:

- `include_payees: list[str]`, read from `INCLUDE_PAYEES` (comma-separated,
  default empty)
- `exclude_payees: list[str]`, read from `EXCLUDE_PAYEES` (comma-separated,
  default empty)

### Wiring into `__main__.py`

In `main()`, after the last existing filter call, add:

```python
transactions = payee_filter.filter_transactions(transactions, config)
```

### `.env.example`

Add `INCLUDE_PAYEES=` and `EXCLUDE_PAYEES=` (commented, matching the existing
style) to the "Analysis" section of `.env.example`, immediately after
`EXCLUDE_CATEGORIES` — so every filtering variant introduced by this task is
discoverable in the template, not just documented in the requirements spec.

### Out of scope (deferred)

- FR-36c (web UI `GET /api/payees` + multiselect lists): deferred until a
  web UI task exists, contingent on Open Item #5 (web framework selection),
  same status as FR-13a/FR-16/FR-30c/FR-35c
- FR-29's CLI `--help` text update to mention `INCLUDE_PAYEES`/
  `EXCLUDE_PAYEES`: out of scope for this task; `--help` wording is covered
  by whichever task next touches `build_arg_parser()` (same deferral
  `account_filter.py`'s TASK-016 applied)

## Branch

**Branch name:** `task/017-payee-filtering`
**Switch/create:** `git checkout -b task/017-payee-filtering`
**Make target:** `make branch-task f=TASK-017`

## Acceptance criteria

- [x] `src/firefly_bills_analyzer/payee_filter.py` exposes
      `filter_transactions(transactions, config) -> list[TransactionRead]`
- [x] When `config.include_payees` is non-empty, only transactions whose
      `destination_name` matches the include list are kept (FR-36a)
- [x] When `config.exclude_payees` is non-empty, transactions whose
      `destination_name` matches the exclude list are dropped (FR-36b);
      exclude is applied after include when both are configured
- [x] Transactions with `destination_name is None` are never matched by a
      non-empty include or exclude list
- [x] When neither list is configured, `filter_transactions` is a passthrough
- [x] `Config` exposes `include_payees: list[str]` and
      `exclude_payees: list[str]`, read from `INCLUDE_PAYEES` and
      `EXCLUDE_PAYEES` (both default empty)
- [x] `__main__.py`'s `main()` calls
      `payee_filter.filter_transactions(transactions, config)` after the
      other filter calls, before `analyzer.identify_recurring()`
- [x] `.env.example` includes commented `INCLUDE_PAYEES=`/`EXCLUDE_PAYEES=`
      lines in the Analysis section, after `EXCLUDE_CATEGORIES`
- [x] `tests/test_payee_filter.py` uses **Hypothesis** for the
      include/exclude/passthrough combinations, mirroring
      `tests/test_account_filter.py`'s structure
- [x] `make lint && make test` pass with coverage >= baseline

## Blockers

None

## Completion

**Date:** 2026-07-20
**Summary:** Implemented `payee_filter.py` mirroring `account_filter.py`'s
include/exclude structure (pure include/exclude, no confidence weighting),
matching `destination_name` instead of `source_name`. Added
`include_payees`/`exclude_payees` to `Config`, read from
`INCLUDE_PAYEES`/`EXCLUDE_PAYEES`. Wired
`payee_filter.filter_transactions()` into `__main__.main()` right after the
existing account filter call. `tests/test_payee_filter.py` (written by the
Test Writer agent) covers passthrough, include, exclude,
exclude-after-include, and the `destination_name is None` non-match cases
with Hypothesis. Existing `Config(...)` call sites across the test suite
(`test_analyzer.py`, `test_bills_creator.py`, `test_fetcher.py`,
`test_category_filter.py`, `test_account_filter.py`, `benchmark_analyzer.py`)
and the `test_main.py` pipeline-wiring mocks were updated for the two new
required fields. `.env.example` gained commented `INCLUDE_PAYEES=`/
`EXCLUDE_PAYEES=` lines after `EXCLUDE_CATEGORIES`. Also fixed a pre-existing
`make lint` failure (MD018 false-positive in
`docs/REQUIREMENTS_new.md:662`, where a line-wrapped "#5)" was mistaken for
an ATX heading) via a pure rewrap with no content change, since it blocked
the mandatory lint gate and TASK-016 had left it unresolved. `make lint &&
make test` pass (165 tests, 99% coverage, matching the TASK-016 baseline).

**Files changed:**

- `src/firefly_bills_analyzer/payee_filter.py` — new (`filter_transactions()`,
  FR-36a/FR-36b)
- `tests/test_payee_filter.py` — new (written by Test Writer agent;
  Hypothesis-based coverage of passthrough, include, exclude,
  exclude-after-include, and `destination_name is None` non-match cases)
- `src/firefly_bills_analyzer/config.py` — modified (`include_payees`/
  `exclude_payees` fields, read from `INCLUDE_PAYEES`/`EXCLUDE_PAYEES`)
- `src/firefly_bills_analyzer/__main__.py` — modified (imports `payee_filter`
  and wires `payee_filter.filter_transactions()` into `main()` after the
  account filter call)
- `.env.example` — modified (commented `INCLUDE_PAYEES=`/`EXCLUDE_PAYEES=`
  lines in the Analysis section, after `EXCLUDE_CATEGORIES`)
- `tests/test_main.py` — modified (patches `payee_filter.filter_transactions`
  in the pipeline-wiring test fixture; asserts it's called after the account
  filter and before analyze)
- `tests/test_analyzer.py` — modified (added the two new required `Config`
  fields to `_make_config()`)
- `tests/test_bills_creator.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `tests/test_fetcher.py` — modified (added the two new required `Config`
  fields to `_make_config()`)
- `tests/test_category_filter.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `tests/test_account_filter.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `tests/benchmark_analyzer.py` — modified (added the two new required
  `Config` fields to `_make_config()`)
- `docs/REQUIREMENTS_new.md` — modified (pure rewrap fix for a pre-existing
  MD018 false-positive, no content change)
- `CHANGELOG.md` — modified (Unreleased entry for `INCLUDE_PAYEES`/
  `EXCLUDE_PAYEES`)
- `docs/tasks/README.md` — modified (status)
- `docs/tasks/TASK-017-payee-filtering.md` — this file

**Branch:** `git checkout task/017-payee-filtering`
**Stage:** `git add src/firefly_bills_analyzer/payee_filter.py tests/test_payee_filter.py src/firefly_bills_analyzer/config.py src/firefly_bills_analyzer/__main__.py .env.example tests/test_main.py tests/test_analyzer.py tests/test_bills_creator.py tests/test_fetcher.py tests/test_category_filter.py tests/test_account_filter.py tests/benchmark_analyzer.py docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/README.md docs/tasks/TASK-017-payee-filtering.md`
**Commit:** `git commit -m "feat: add payee filtering functionality (UC10) with INCLUDE_PAYEES/EXCLUDE_PAYEES support"`
