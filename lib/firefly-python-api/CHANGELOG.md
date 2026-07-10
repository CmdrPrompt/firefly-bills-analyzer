# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `FireflyClient(url, token)` wraps `requests.Session` with `Authorization: Bearer`, `Accept: application/json`, and `Content-Type: application/json` headers (TASK-001)
- `FireflyClient.validate_connection()` verifies server reachability via `GET /api/v1/about`; raises `FireflyConnectionError` on network or HTTP failure (TASK-001)
- `load_config(env_path)` reads `FIREFLY_URL` and `FIREFLY_TOKEN` from the environment or a `.env` file; raises `ValueError` when either value is absent (TASK-001)
- `FireflyClient.get_asset_accounts()` fetches all asset accounts with automatic pagination (TASK-002)
- `FireflyClient.get_latest_transaction_date(account_id)` returns the most recent transaction date as `YYYY-MM-DD` or `None` (TASK-002)
- `FireflyClient.create_transaction(payload)` posts a transaction and raises `FireflyConnectionError` on failure (TASK-002)
- `FireflyClient.get_bills()`, `get_budgets()`, `get_budget_limits(budget_id)`, `get_categories()`, and `get_summary(start, end)` provide read-only access to Firefly III reporting resources (TASK-002)
- Read-only integration test suite (`make test-integration`) verified against a real Firefly III instance; credentials loaded from `config.json`/`secrets.json` or environment (TASK-003)
- `TypedDict` types `AssetAccount`, `TransactionPayload`, `BillData`, `BudgetData`, `BudgetLimitData`, `CategoryData` exported from `firefly_python_api` for IDE code completion and `mypy` type checking (TASK-004)
- `FireflyClient.get_withdrawal_transactions(start, end)` fetches all withdrawal transactions in a date range, following pagination automatically and flattening multi-split transactions into individual `TransactionRead` records (`date`, `amount`, `destination_name`, `category_name`) (TASK-005)
- `FireflyClient.create_bill(payload)` registers a new recurring bill via `POST /api/v1/bills`, treating HTTP 200/201 as success and raising `FireflyConnectionError` on any other status (including a duplicate bill name) or network error; `BillPayload` `TypedDict` (`name`, `amount_min`, `amount_max`, `date`, `repeat_freq`, `active`) exported from `firefly_python_api` (TASK-006)

### Fixed
- `get_summary()` now requires `start` and `end` date parameters as mandated by the Firefly III API (TASK-003)
