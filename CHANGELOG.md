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
- `FireflyConnectionError` raised by `create_bill()` on a non-2xx response now carries `status_code` and `response_body` (parsed JSON, or `None` for a non-JSON body or a network-level failure), letting callers distinguish a 422 duplicate-name rejection from other failures without re-parsing HTTP internals (TASK-007)
- `TransactionRead` records returned by `get_withdrawal_transactions()` now also carry `source_name` and `source_id` (the account funds are withdrawn from), defaulting to `None` when absent from the API response, so consumers can plan balance transfers ahead of recurring withdrawals (TASK-010)
- `get_withdrawal_transactions(start, end, on_page=None)` accepts an optional `on_page(page, total_pages)` callback invoked after each page is fetched, letting consumers drive a progress indicator during long-running imports without this library depending on any progress-bar package; omitting it leaves behavior unchanged (TASK-011)
- `FireflyClient.get_transactions_for_account(account_id)` fetches all transaction IDs for an account with automatic pagination, and `FireflyClient.delete_transaction(transaction_id)` deletes a transaction (treating HTTP 204 as success), so consumers can implement a "clear transactions for selected accounts" reimport flow without duplicating pagination and HTTP error handling (TASK-012)
- `FireflyClient.set_opening_balance(account_id, balance, date)` sets an account's opening balance and opening balance date via `PUT /api/v1/accounts/{id}`, treating HTTP 200 as success and raising `FireflyConnectionError` (with `status_code`/`response_body`) on any other status or network error, so consumers can establish a correct starting balance after clearing and re-importing transaction history (TASK-013)
- `FireflyClient.get_opening_balance(account_id)` reads an account's current opening balance and opening balance date via `GET /api/v1/accounts/{id}`, returning an `OpeningBalance` `TypedDict` (`balance`, `date`, both `None` when unset) so consumers can decide whether `set_opening_balance()` needs to be called at all (TASK-014)
- `get_latest_transaction_date(account_id, transaction_type=None)` accepts an optional Firefly III transaction type filter (e.g. `"withdrawal,deposit"`), forwarded as the `type` query parameter, so consumers can exclude transfer transactions from the duplicate-import floor date; omitting it leaves behavior unchanged (TASK-015)
- `FireflyClient.get_deposit_transactions(start, end, on_page=None)` fetches all deposit transactions in a date range with the same pagination and split-flattening as `get_withdrawal_transactions()`; since the `type=deposit` filter excludes transfers between the user's own asset accounts, every returned record represents money entering from outside, letting consumers detect recurring income (e.g. salary) without hand-maintained configuration (TASK-016)
- `TransactionRead` records now carry `tags: list[str]`, read from each split's `attributes.transactions[].tags` and preserved exactly as returned (no case-folding, trimming, or sorting); an absent or `null` tags field becomes `[]`, never `None`, so a consumer can mark individual transactions (e.g. a shared grocery purchase) without reorganizing categories (TASK-017)

### Changed
- Test suite for `create_bill()`'s `status_code`/`response_body` exception attributes now asserts against the real `requests.exceptions.JSONDecodeError` (instead of a bare `ValueError`) for the non-JSON error body case, and consolidates the 422/500 non-success scenarios into one parametrized test with no loss of scenario traceability (TASK-008, TASK-009)

### Fixed
- `get_summary()` now requires `start` and `end` date parameters as mandated by the Firefly III API (TASK-003)
