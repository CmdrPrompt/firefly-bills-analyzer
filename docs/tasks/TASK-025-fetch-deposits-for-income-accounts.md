# TASK-025 Fetch deposits for configured income accounts (UC12)

## Status

blocked

## Requirements

**Binding:** FR-39a, FR-39b, FR-39c, FR-40a, FR-40b, FR-40c, FR-40d, NFR-13, NFR-14
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-002 (`fetcher.py`, whose lookback-window computation and
client construction this mirrors), TASK-007 (cache layer)
**Blocked on:** `firefly-python-api` REQ-011 / that repository's TASK-016
(`get_deposit_transactions()`), which does not exist yet
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

- [ ] Scenario: No income account configured means no deposit fetch
      Given `INCOME_ACCOUNTS` is empty
      When the analysis runs
      Then no deposit request is made, no client is constructed for one, and
      the run's behavior is identical to today's

- [ ] Scenario: Deposits are fetched for the configured window
      Given `INCOME_ACCOUNTS` names one account and `LOOKBACK_MONTHS` is 24
      When the analysis runs
      Then `get_deposit_transactions()` is called with the same start and end
      dates `fetch_transactions()` used in that run

- [ ] Scenario: Deposits to other accounts are discarded
      Given deposits landing on both a configured income account and an
      unconfigured account
      When `fetch_deposits()` returns
      Then only the records whose `destination_name` matches an income account
      are present

- [ ] Scenario: Deposits never reach the withdrawal pipeline
      Given a run with income accounts configured
      When the analysis completes
      Then no deposit record is passed to payee grouping, category filtering,
      account filtering, payee filtering, or bill creation, asserted at the
      call boundaries

- [ ] Scenario: Deposits are cached under their own key
      Given a completed run with income accounts configured
      When the cache directory is inspected
      Then a `deposits` cache entry exists, distinct from the `transactions`
      entry, and a second run within `CACHE_TTL_TRANSACTIONS` makes no deposit
      request

- [ ] Scenario: A cached window mismatch forces a refetch
      Given a cached deposit entry whose window differs from the current run's
      When the analysis runs
      Then the deposits are fetched again rather than read from cache

- [ ] Scenario: An unreachable instance is reported, not crashed
      Given the deposit fetch raises `FireflyConnectionError`
      When the analysis runs
      Then the error is reported per NFR-04, with no stack trace

- [ ] Hypothesis property test: for any set of deposit records and any set of
      configured income account names, every record in the result has a
      `destination_name` in that set, and no record with a matching
      `destination_name` is dropped

- [ ] `make lint && make test` pass with coverage >= the task-start baseline

## Out of scope

- Recognizing which deposits constitute an income source, and the observed net
  income and variance figures (TASK-026).
- The income export and its CLI display (TASK-027).
- Any income-side equivalent of the include/exclude filters. The income account
  list is the only narrowing on this side.
- Adding `destination_id` to the client's `TransactionRead`. Matching by name
  matches how `account_filter` already works.

## Blockers

`firefly-python-api` does not expose `get_deposit_transactions()`. Requirement
REQ-011 and TASK-016 have been written in that repository; the method itself is
not implemented. Do not start this task until it is merged and the vendored
`lib/firefly-python-api` copy has been re-synced.

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
