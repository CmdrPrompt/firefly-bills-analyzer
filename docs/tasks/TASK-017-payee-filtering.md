# TASK-017 Filter transactions by payee / destination account (UC10)

## Status

not started

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

- [ ] `src/firefly_bills_analyzer/payee_filter.py` exposes
      `filter_transactions(transactions, config) -> list[TransactionRead]`
- [ ] When `config.include_payees` is non-empty, only transactions whose
      `destination_name` matches the include list are kept (FR-36a)
- [ ] When `config.exclude_payees` is non-empty, transactions whose
      `destination_name` matches the exclude list are dropped (FR-36b);
      exclude is applied after include when both are configured
- [ ] Transactions with `destination_name is None` are never matched by a
      non-empty include or exclude list
- [ ] When neither list is configured, `filter_transactions` is a passthrough
- [ ] `Config` exposes `include_payees: list[str]` and
      `exclude_payees: list[str]`, read from `INCLUDE_PAYEES` and
      `EXCLUDE_PAYEES` (both default empty)
- [ ] `__main__.py`'s `main()` calls
      `payee_filter.filter_transactions(transactions, config)` after the
      other filter calls, before `analyzer.identify_recurring()`
- [ ] `.env.example` includes commented `INCLUDE_PAYEES=`/`EXCLUDE_PAYEES=`
      lines in the Analysis section, after `EXCLUDE_CATEGORIES`
- [ ] `tests/test_payee_filter.py` uses **Hypothesis** for the
      include/exclude/passthrough combinations, mirroring
      `tests/test_account_filter.py`'s structure
- [ ] `make lint && make test` pass with coverage >= baseline

## Blockers

None

## Completion

(fill in after implementation)
