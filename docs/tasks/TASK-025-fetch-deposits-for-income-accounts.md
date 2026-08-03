# TASK-025 Fetch deposits for configured income accounts (UC12)

## Status

done

## Requirements

**Binding:** FR-39a, FR-39b, FR-39c, FR-40a, FR-40b, FR-40c, FR-40d, NFR-13, NFR-14
**BDD mode:** BDD-ACTIVE
**Depends on:** TASK-002 (`fetcher.py`, whose lookback-window computation and
client construction this mirrors), TASK-007 (cache layer)
**Blocked on:** Resolved — see Blockers section below.
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user who wants a cost split based on what I actually earn, I want the
application to read the deposits landing on my salary account, so that the
income figure comes from my transaction history rather than from a number I
typed into a config file once and have not revisited since my last raise.

## Description

Add the deposit-side ingestion path. This task ends where the raw, filtered
deposits are in memory; recognizing an income source from them is TASK-026.

Configuration (`config.py`), following `account_filter`'s comma-separated
convention rather than inventing a new one:

- `income_accounts: list[str]` from `INCOME_ACCOUNTS`, empty disables the
  feature (FR-39a)
- `income_min_occurrences: int` from `INCOME_MIN_OCCURRENCES`, default 3 (FR-39b)
- `income_variance_tolerance: float` from `INCOME_VARIANCE_TOLERANCE`, default
  0.10 (FR-39c)

FR-39b and FR-39c are read here rather than in TASK-026 so that the whole
`INCOME_*` block lands in `Config` in one change, and every existing
`Config(...)` call site in the test suite is touched once instead of twice.

Fetching (`fetcher.py`, new `fetch_deposits(config)`):

- Same window as `fetch_transactions()`: today minus `lookback_months`, same
  `_subtract_months` clamping. Reuse the helper; do not re-derive it.
- Calls `client.get_deposit_transactions(start, end, on_page=...)`, driving the
  same `tqdm` progress bar `fetch_transactions()` uses (FR-34's mechanism,
  applied to the second fetch).
- Returns `[]` immediately, without constructing a client or touching the
  network, when `config.income_accounts` is empty (FR-40b, NFR-14).
- Discards every record whose `destination_name` is not an income account
  (FR-40c). Note the inversion: on a deposit, `destination_name` is the asset
  account that received the money, and `source_name` is the payer. This is
  Firefly III's own convention, not something the client normalizes.
- Caches under its own key, `deposits`, with `cache_ttl_transactions` and the
  same window-match guard `fetch_transactions()` applies (NFR-13). A separate
  key, not a shared one: the two fetches have different filters and must not
  invalidate or satisfy each other.

Wiring (`cli.py`): call `fetch_deposits()` after `fetch_transactions()`. The
result is not passed to `payee_filter`, `category_filter`, `account_filter`,
`analyzer.identify_recurring()`, or `bills_creator` (FR-40d). Until TASK-026
lands, the fetched list is unused beyond a debug log; that is deliberate, so
this task can merge behind its blocker without a half-built detector.

## Branch

**Branch name:** `task/025-fetch-deposits-for-income-accounts`
**Switch/create:** `git checkout -b task/025-fetch-deposits-for-income-accounts`
**Make target:** `make branch-task f=TASK-025`

## Acceptance criteria (Gherkin)

**Feature files:** tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature

- [x] 1. Scenario: No income account configured means no deposit fetch
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "No income account configured means no deposit fetch"

- [x] 2. Scenario: Deposits are fetched for the configured window
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "Deposits are fetched for the configured window"

- [x] 3. Scenario: Deposits to other accounts are discarded
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "Deposits to other accounts are discarded"

- [x] 4. Scenario: Deposits never reach the withdrawal pipeline
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "Deposits never reach the withdrawal pipeline"

- [x] 5. Scenario: Deposits are cached under their own key
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "Deposits are cached under their own key"

- [x] 6. Scenario: A cached window mismatch forces a refetch
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "A cached window mismatch forces a refetch"

- [x] 7. Scenario: An unreachable instance is reported, not crashed
      See tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature: Scenario "An unreachable instance is reported, not crashed"

- [x] 8. Hypothesis property test: for any set of deposit records and any set of
      configured income account names, every record in the result has a
      `destination_name` in that set, and no record with a matching
      `destination_name` is dropped

- [x] 9. `make lint && make test` pass with coverage >= the task-start baseline

## Out of scope

- Recognizing which deposits constitute an income source, and the observed net
  income and variance figures (TASK-026).
- The income export and its CLI display (TASK-027).
- Any income-side equivalent of the include/exclude filters. The income account
  list is the only narrowing on this side.
- Adding `destination_id` to the client's `TransactionRead`. Matching by name
  matches how `account_filter` already works.

## Blockers

Resolved. `firefly-python-api`'s TASK-016 (REQ-011) shipped
`FireflyClient.get_deposit_transactions(start, end, on_page=None)`; the
vendored copy at `lib/firefly-python-api` has been re-synced and the method is
implemented (not a stub) in
`lib/firefly-python-api/src/firefly_python_api/_client.py` lines 542-581,
delegating to the same `_get_transactions_by_type` pagination helper as
`get_withdrawal_transactions()`. Confirmed via
`lib/firefly-python-api/CHANGELOG.md` [Unreleased] entry (TASK-016) and by
importing `FireflyClient.get_deposit_transactions` directly from the vendored
source, which shows a matching signature
`(start, end, on_page=None) -> list[TransactionRead]`.

## Completion

**Date:** 2026-08-03
**Summary:** Added `INCOME_ACCOUNTS`/`INCOME_MIN_OCCURRENCES`/`INCOME_VARIANCE_TOLERANCE`
to `Config`, and a new `fetch_deposits(config)` in `fetcher.py` that mirrors
`fetch_transactions()`'s window derivation, `tqdm` progress, and cache-guard
logic, but calls `get_deposit_transactions()`, filters to configured income
accounts by `destination_name`, and caches under a separate `deposits` key.
`fetch_deposits()` is a no-op (no client, no cache/network access) when
`income_accounts` is empty. Wired into `__main__.main()` after
`fetch_transactions()`; its result is only debug-logged, not passed to any
downstream filter/analyzer/creator. All pre-existing `Config(...)` test
call-site helpers were updated for the three new required fields.
**Files changed:**

- `src/firefly_bills_analyzer/config.py` - modified
- `src/firefly_bills_analyzer/fetcher.py` - modified
- `src/firefly_bills_analyzer/__main__.py` - modified
- `tests/test_fetcher.py` - modified
- `tests/test_config.py` - pre-existing (Test Writer)
- `tests/test_main.py` - pre-existing (Test Writer)
- `tests/test_account_filter.py` - modified
- `tests/test_analyzer.py` - modified
- `tests/test_bills_creator.py` - modified
- `tests/test_category_filter.py` - modified
- `tests/test_payee_filter.py` - modified
- `tests/benchmark_analyzer.py` - modified
- `tests/bdd/steps/test_task_019_steps.py` - modified
- `tests/bdd/steps/test_task_025_steps.py` - modified (fixed two `_today` staleness bugs)
- `tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature` - pre-existing (Test Writer)
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-025-fetch-deposits-for-income-accounts.md` - modified

**Branch:** `git checkout task/025-fetch-deposits-for-income-accounts`
**Stage:** `git add src/firefly_bills_analyzer/config.py src/firefly_bills_analyzer/fetcher.py src/firefly_bills_analyzer/__main__.py tests/test_fetcher.py tests/test_config.py tests/test_main.py tests/test_account_filter.py tests/test_analyzer.py tests/test_bills_creator.py tests/test_category_filter.py tests/test_payee_filter.py tests/benchmark_analyzer.py tests/bdd/steps/test_task_019_steps.py tests/bdd/steps/test_task_025_steps.py tests/bdd/features/TASK-025-fetch-deposits-for-income-accounts.feature CHANGELOG.md docs/tasks/TASK-025-fetch-deposits-for-income-accounts.md`
**Commit:** `git commit -m "Fetch deposits for configured income accounts (TASK-025)"`
