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

### Fixed
- `get_summary()` now requires `start` and `end` date parameters as mandated by the Firefly III API (TASK-003)
