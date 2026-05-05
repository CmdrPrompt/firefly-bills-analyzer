# TASK-002 Account, transaction, and reporting methods

## Status
done

## Description

Extend `FireflyClient` with all API methods defined in REQ-002 and REQ-003.

REQ-002 covers the operations used by `firefly-bank-importer`: fetching asset
accounts (paginated), retrieving the latest transaction date for an account, and
creating transactions. REQ-003 covers the read-only reporting methods needed by
`firefly-bills-analyzer`: bills, budgets, budget limits, categories, and summary.

TASK-001 must be merged before this task begins.

## Branch
**Branch name:** `task/002-api-methods`
**Switch/create:** `git checkout -b task/002-api-methods`
**Make target:** `make branch-task f=TASK-002`

## Acceptance criteria

- [x] TASK-001 is merged and on `main`
- [x] `FireflyClient.get_asset_accounts()` calls paginated
  `GET /api/v1/accounts?type=asset` and returns a list of
  `{"id": str, "name": str}` dicts covering all pages
- [x] `FireflyClient.get_latest_transaction_date(account_id)` calls
  `GET /api/v1/accounts/{id}/transactions?limit=1&page=1` and returns an ISO
  date string (`YYYY-MM-DD`) or `None` if the account has no transactions;
  the raw `YYYY-MM-DD HH:MM:SS` value from the API is truncated to date only
- [x] `FireflyClient.create_transaction(payload)` posts to
  `POST /api/v1/transactions`; HTTP 200 and 201 are treated as success; any
  other status raises `FireflyConnectionError`
- [x] `FireflyClient.get_bills()` calls `GET /api/v1/bills` and returns the
  `data` list
- [x] `FireflyClient.get_budgets()` calls `GET /api/v1/budgets` and returns the
  `data` list
- [x] `FireflyClient.get_budget_limits(budget_id)` calls
  `GET /api/v1/budgets/{id}/limits` and returns the `data` list
- [x] `FireflyClient.get_categories()` calls `GET /api/v1/categories` and
  returns the `data` list
- [x] `FireflyClient.get_summary()` calls `GET /api/v1/summary/basic` and
  returns the response dict
- [x] Unit test coverage for this package is ≥ 90 %
- [x] `make lint && make test` pass

## Completion
**Date:** 2026-04-30
**Summary:** Added all API methods to FireflyClient following TDD. 40 unit tests, 100% coverage.
**Files changed:**
- `src/firefly_python_api/_client.py` — modified
- `tests/test_api_methods.py` — created
- `CHANGELOG.md` — modified
**Branch:** `task/002-api-methods`
**Stage:** `git add src/firefly_python_api/_client.py tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-002-api-methods.md`
**Commit:** `git commit -m "Add account, transaction, and reporting methods to FireflyClient (TASK-002)"`
