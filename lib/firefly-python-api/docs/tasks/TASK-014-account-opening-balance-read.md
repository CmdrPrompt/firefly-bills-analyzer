# TASK-014 Account opening balance read

## Status

done

## Requirements

**Binding:** REQ-010
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bank-importer), I want a method to
read an account's current opening balance and opening balance date via
`FireflyClient`, so that I can decide whether `set_opening_balance()` needs
to be called at all before clearing and re-importing transaction history,
without reimplementing the HTTP call.

## Description

Add `FireflyClient.get_opening_balance(account_id)` — a method that GETs
`/api/v1/accounts/{id}` and returns an `OpeningBalance` `TypedDict` with
`balance: str | None` and `date: str | None`, read from the response's
`attributes.opening_balance` and `attributes.opening_balance_date`,
defaulting to `None` when the account has no opening balance set.

Uses the existing `_get` helper (same behavior as `get_asset_accounts()` and
`get_latest_transaction_date()`); raises `FireflyConnectionError` on any
network error or non-2xx HTTP response, including a 404 for an unknown
`account_id`. No new HTTP helper is needed — this is a read, not a write.

Add the `OpeningBalance` `TypedDict` to `_types.py` and export it from
`firefly_python_api`, alongside the existing typed return values
(`AssetAccount`, `TransactionRead`, etc.).

## Branch

**Branch name:** `task/014-account-opening-balance-read`
**Switch/create:** `git checkout -b task/014-account-opening-balance-read`
**Make target:** `make branch-task f=TASK-014`

## Acceptance criteria (Gherkin)

Scenarios are inline (BDD-ABSENT) and lift-ready for `.feature` extraction if
BDD tooling is adopted later.

- [x] Scenario: Opening balance is read successfully
      Given a valid account id whose account has an opening balance set
      When `get_opening_balance(account_id)` is called and the API responds
      with HTTP 200
      Then it returns an `OpeningBalance` with `balance` and `date` taken
      from `attributes.opening_balance` and `attributes.opening_balance_date`
      And the request was a GET to `/api/v1/accounts/{account_id}`

- [x] Scenario: Account has no opening balance set
      Given a valid account id whose account has no opening balance
      When `get_opening_balance(account_id)` is called and the API responds
      with HTTP 200 and `attributes.opening_balance`/`opening_balance_date`
      absent or `null`
      Then it returns an `OpeningBalance` with `balance` and `date` both
      `None`

- [x] Scenario: Read fails on a non-2xx status (e.g. unknown account id)
      Given an account id that does not exist
      When `get_opening_balance(account_id)` is called and the API responds
      with HTTP 404
      Then a `FireflyConnectionError` is raised

- [x] Scenario: Read fails on a network/connection error
      Given a valid account id
      When `get_opening_balance(account_id)` is called and the underlying
      HTTP request fails with a connection error
      Then a `FireflyConnectionError` is raised

- [x] Scenario: Type checking and quality gates pass
      Given the completed implementation of `get_opening_balance` and the
      `OpeningBalance` `TypedDict`
      When `mypy --strict` is run on `src/`, and `make lint && make test` are
      run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Any consumer-side decision logic for comparing the read balance against a
  desired value before calling `set_opening_balance()` — tracked separately
  in the consumer project's own requirements/task docs.
- Reading any other account field (name, type, current balance, etc.) —
  only `opening_balance` and `opening_balance_date`.

## Blockers

None.

## Completion

**Date:** 2026-07-20
**Summary:** Added the `OpeningBalance` `TypedDict` (`balance`, `date`, both `str | None`) to `_types.py` and exported it from `firefly_python_api`, plus `FireflyClient.get_opening_balance(account_id)`, which GETs `/api/v1/accounts/{id}` via the existing `_get` helper and reads `attributes.opening_balance`/`attributes.opening_balance_date`, defaulting both to `None` when absent or `null`. Covered by 5 new unit tests (balance present, absent, explicitly `null`, 404, connection error) plus 1 new read-only integration test against a real Firefly III instance (matching `get_bills`/`get_asset_accounts` — read-only, so it doesn't run into the "no write operations" limitation that excluded TASK-013 from integration coverage). All 115 unit tests pass with 100% coverage (no regression from the 100%/110-test baseline). ruff check, ruff format --check, mypy --strict, bandit, and complexipy all pass cleanly; `make lint`'s `check-agents-sync` failure is pre-existing on `main` and unrelated to files touched by this task.
**Files changed:**
- `src/firefly_python_api/_client.py` - modified
- `src/firefly_python_api/_types.py` - modified
- `src/firefly_python_api/__init__.py` - modified
- `tests/test_api_methods.py` - modified
- `tests/integration/test_integration.py` - modified
- `CHANGELOG.md` - modified
- `docs/REQUIREMENTS.md` - modified
- `docs/tasks/TASK-014-account-opening-balance-read.md` - modified
**Branch:** `git checkout task/014-account-opening-balance-read`
**Stage:** `git add src/firefly_python_api/_client.py src/firefly_python_api/_types.py src/firefly_python_api/__init__.py tests/test_api_methods.py tests/integration/test_integration.py CHANGELOG.md docs/REQUIREMENTS.md docs/tasks/TASK-014-account-opening-balance-read.md`
**Commit:** `git commit -m "Add account opening balance read to FireflyClient"`
