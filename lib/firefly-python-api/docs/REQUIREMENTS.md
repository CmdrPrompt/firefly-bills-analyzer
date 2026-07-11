# firefly-python-api — Requirements

## Purpose

A standalone Python client library for the Firefly III REST API.
It owns the HTTP session lifecycle, credential loading, and API coverage
for accounts, transactions, and reporting resources. It has no knowledge
of any consumer project's configuration flow.

## REQ-001 HTTP Session and Credential Management

**As a** consumer application,
**I want** a single object that manages an authenticated HTTP session,
**so that** I don't need to construct requests.Session or inject auth headers manually.

### Use cases

- UC-001-1: Instantiate `FireflyClient(url, token)` — wraps `requests.Session`
  with `Authorization: Bearer <token>`, `Accept: application/json`, and
  `Content-Type: application/json` headers.
- UC-001-2: Call `load_config(env_path)` — reads `FIREFLY_URL` and `FIREFLY_TOKEN`
  from environment or `.env` file; returns `(url, token)`.
- UC-001-3: Call `FireflyClient.validate_connection()` — `GET /api/v1/about`;
  raises `FireflyConnectionError` on failure.

### Constraints

- Runtime dependencies limited to `requests` and `python-dotenv`.
- Unit test coverage ≥ 90 %.

## REQ-002 Account and Transaction Methods

**As a** consumer application,
**I want** methods on `FireflyClient` for common account and transaction operations,
**so that** I don't duplicate HTTP calls across multiple projects.

### Use cases

- UC-002-1: `get_asset_accounts()` — paginated `GET /api/v1/accounts?type=asset`;
  returns list of `{"id": str, "name": str}` dicts, all pages fetched automatically.
- UC-002-2: `get_latest_transaction_date(account_id)` —
  `GET /api/v1/accounts/{id}/transactions?limit=1&page=1`;
  returns an ISO date string (`YYYY-MM-DD`) or `None` if the account has no
  transactions. The raw API value (`YYYY-MM-DD HH:MM:SS`) is truncated to date only.
- UC-002-3: `create_transaction(payload)` — `POST /api/v1/transactions`;
  treats HTTP 200 and 201 as success; raises `FireflyConnectionError` on any
  other status code.

### Constraints

- Unit test coverage ≥ 90 %.

## REQ-003 Reporting and Resource Read Methods

**As a** consumer application,
**I want** read-only methods for bills, budgets, categories, and summary,
**so that** reporting tools can access Firefly III data without reimplementing HTTP calls.

### Use cases

- UC-003-1: `get_bills()` — `GET /api/v1/bills`; returns `data` list.
- UC-003-2: `get_budgets()` — `GET /api/v1/budgets`; returns `data` list.
- UC-003-3: `get_budget_limits(budget_id)` — `GET /api/v1/budgets/{id}/limits`;
  returns `data` list.
- UC-003-4: `get_categories()` — `GET /api/v1/categories`; returns `data` list.
- UC-003-5: `get_summary(start, end)` — `GET /api/v1/summary/basic?start=YYYY-MM-DD&end=YYYY-MM-DD`;
  returns the response dict. Both `start` and `end` are required by the Firefly III API.

### Constraints

- Unit test coverage ≥ 90 %.

## REQ-004 Integration Tests

**As a** developer,
**I want** a suite of integration tests that connect to a real Firefly III instance,
**so that** I can verify the library works end-to-end against actual API responses.

### Use cases

- UC-004-1: `validate_connection()` succeeds against the configured instance.
- UC-004-2: `get_asset_accounts()` returns a non-empty list of accounts.
- UC-004-3: `get_latest_transaction_date(account_id)` returns a date string or
  `None` for the first account returned by `get_asset_accounts()`.
- UC-004-4: `get_bills()`, `get_budgets()`, `get_categories()`, and `get_summary()`
  return without error.

### Constraints

- Integration tests live in `tests/integration/` and are excluded from `make test`.
- Run with `make test-integration`.
- Credentials are read via `load_config()` from a `.env` file or environment.
- No write operations (`create_transaction`) are included — read-only only.
- Tests are skipped automatically if `FIREFLY_URL` or `FIREFLY_TOKEN` is absent.

## REQ-005 Typed Return Values

**As a** developer using an IDE,
**I want** concrete types for the data structures returned by `FireflyClient`,
**so that** I get accurate code completion and type checking in VS Code and mypy.

### Use cases

- UC-005-1: `get_asset_accounts()` returns `list[AssetAccount]` where
  `AssetAccount` is a `TypedDict` with keys `id: str` and `name: str`.
- UC-005-2: `get_latest_transaction_date()` return type remains `str | None`
  (already precise).
- UC-005-3: `create_transaction(payload)` accepts a `TransactionPayload`
  `TypedDict` describing the required and optional fields:
  `type`, `date`, `amount`, `description`, `source_id`, `destination_id`,
  `currency_code`.
- UC-005-4: `get_bills()`, `get_budgets()`, `get_budget_limits()`, and
  `get_categories()` return `list[BillData]`, `list[BudgetData]`,
  `list[BudgetLimitData]`, and `list[CategoryData]` respectively — each a
  `TypedDict` with at least `id: str` and `attributes: dict[str, Any]`.
- UC-005-5: `get_summary()` return type remains `dict[str, Any]`
  (summary structure varies by Firefly configuration).
- UC-005-6: All `TypedDict` types are importable from `firefly_python_api`.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.

## REQ-006 Withdrawal Transaction Fetching

**As a** consumer application (e.g. firefly-bills-analyzer),
**I want** a method that returns all withdrawal transactions in a date range as typed data,
**so that** I can analyze spending/recurring payments without reimplementing pagination
or Firefly III's split-transaction structure.

### Use cases

- UC-006-1: `get_withdrawal_transactions(start, end)` — paginated
  `GET /api/v1/transactions?type=withdrawal&start=YYYY-MM-DD&end=YYYY-MM-DD&page=N`;
  follows all pages until `total_pages` is reached; returns `list[TransactionRead]`.
- UC-006-2: Each Firefly III transaction object may contain multiple splits under
  `attributes.transactions`; each split is flattened into its own `TransactionRead` entry.
- UC-006-3: `TransactionRead` is a `TypedDict` with `date: str` (truncated to `YYYY-MM-DD`),
  `amount: str`, `destination_name: str | None`, `category_name: str | None` — the latter
  two default to `None` when absent from the API response.
- UC-006-4: `TransactionRead` is exported from `firefly_python_api`.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.

## REQ-007 Bill Creation

**As a** consumer application (e.g. firefly-bills-analyzer),
**I want** a method to create a new bill via `FireflyClient`,
**so that** I can programmatically register recurring bills without duplicating HTTP calls.

### Use cases

- UC-007-1: `create_bill(bill)` — `POST /api/v1/bills`; treats HTTP 200 and 201 as
  success; raises `FireflyConnectionError` on any other status code (including 422
  for a duplicate bill name).
- UC-007-2: `create_bill(payload)` accepts a `BillPayload` `TypedDict` with required
  fields: `name: str`, `amount_min: str`, `amount_max: str`, `date: str`
  (`YYYY-MM-DD`), `repeat_freq: str`, `active: bool`. `repeat_freq` values accepted
  by the Firefly III API are `weekly`, `monthly`, `quarterly`, `half-year`, `yearly`;
  the client does not validate this value before sending — invalid values are
  rejected by the API.
- UC-007-3: `BillPayload` is importable from `firefly_python_api`.
- UC-007-4: When `create_bill()` raises `FireflyConnectionError` because the
  response status was outside 200/201, the exception carries the failed
  response's `status_code: int` and, when the response body is valid JSON,
  `response_body: dict[str, Any]` (both default to `None`, e.g. for a
  network-level failure with no response at all). This lets a caller
  distinguish a 422 "name already in use" validation error from any other
  non-2xx status without re-parsing HTTP internals itself.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.
- UC-007-4 must not change behavior for existing callers of `create_bill()`,
  `create_transaction()`, or any `_get`/`_post` caller — only add attributes
  to the exception already raised.
