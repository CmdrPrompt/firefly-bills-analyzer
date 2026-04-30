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
- `FireflyClient.get_bills()`, `get_budgets()`, `get_budget_limits(budget_id)`, `get_categories()`, and `get_summary()` provide read-only access to Firefly III reporting resources (TASK-002)
