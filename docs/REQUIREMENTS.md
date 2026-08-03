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
- UC-002-2: `get_latest_transaction_date(account_id, transaction_type=None)` —
  `GET /api/v1/accounts/{id}/transactions?limit=1&page=1`, plus a
  `type={transaction_type}` query parameter when `transaction_type` is given
  (e.g. `"withdrawal,deposit"` to exclude transfers, per Firefly III's
  transaction type filter). Returns an ISO date string (`YYYY-MM-DD`) or
  `None` if no matching transaction exists. The system shall truncate the
  raw API value (`YYYY-MM-DD HH:MM:SS`) to date only (`YYYY-MM-DD`) before
  returning it. When `transaction_type` is omitted, behavior is unchanged
  from today (no `type` filter, matches any transaction).
- UC-002-3: `create_transaction(payload)` — `POST /api/v1/transactions`;
  treats HTTP 200 and 201 as success; raises `FireflyConnectionError` on any
  other status code.
- UC-002-4: `get_transactions_for_account(account_id)` — paginated
  `GET /api/v1/accounts/{id}/transactions`; returns a list of transaction IDs
  (as strings), all pages fetched automatically.
- UC-002-5: `delete_transaction(transaction_id)` — `DELETE /api/v1/transactions/{id}`;
  treats HTTP 204 as success; raises `FireflyConnectionError` on any other
  status code.
- UC-002-6: A consumer needing the latest date of only ordinary
  (non-transfer) transactions on an account — because transfer transactions
  may be posted with dates later than yet-unprocessed withdrawal/deposit
  rows on the same account — can call
  `get_latest_transaction_date(account_id, transaction_type="withdrawal,deposit")`
  to exclude transfers from the result.

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
- If `FIREFLY_URL` or `FIREFLY_TOKEN` is absent from the environment, then the
  integration test suite shall skip the affected integration tests automatically.

## REQ-005 Typed Return Values

**As a** developer using an IDE,
**I want** concrete types for the data structures returned by `FireflyClient`,
**so that** I get accurate code completion and type checking in VS Code and mypy.

### Use cases

- UC-005-1: `get_asset_accounts()` returns `list[AssetAccount]` where
  `AssetAccount` is a `TypedDict` with keys `id: str` and `name: str`.
- UC-005-2: The system shall return `get_latest_transaction_date()` results
  typed as `str | None`, consistent with the behavior already defined in
  UC-002-2.
- UC-005-3: `create_transaction(payload)` shall accept a `TransactionPayload`
  `TypedDict` describing the fields `type`, `date`, `amount`, `description`,
  `source_id`, `destination_id`, and `currency_code`, of which `type`, `date`,
  `amount`, and `description` are mandatory and `source_id`, `destination_id`,
  and `currency_code` are optional.
- UC-005-4a: `get_bills()` returns `list[BillData]`, a `TypedDict` with at
  least `id: str` and `attributes: dict[str, Any]`.
- UC-005-4b: `get_budgets()` returns `list[BudgetData]`, a `TypedDict` with
  at least `id: str` and `attributes: dict[str, Any]`.
- UC-005-4c: `get_budget_limits()` returns `list[BudgetLimitData]`, a
  `TypedDict` with at least `id: str` and `attributes: dict[str, Any]`.
- UC-005-4d: `get_categories()` returns `list[CategoryData]`, a `TypedDict`
  with at least `id: str` and `attributes: dict[str, Any]`.
- UC-005-5: The system shall return `get_summary(start, end)` results typed
  as `dict[str, Any]`, consistent with the behavior already defined in
  UC-003-5; the summary structure varies by Firefly configuration.
- UC-005-6: The system shall make all `TypedDict` types it defines
  (including `AssetAccount`, `TransactionPayload`, `BillData`, `BudgetData`,
  `BudgetLimitData`, and `CategoryData`) importable directly from
  `firefly_python_api`.

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
- UC-006-2: When a Firefly III transaction object returned by
  `get_withdrawal_transactions()` contains multiple splits under
  `attributes.transactions`, the system shall flatten each split into its
  own `TransactionRead` entry.
- UC-006-3: The system shall represent each withdrawal transaction split as
  a `TransactionRead` `TypedDict` with fields `date: str` (truncated to
  `YYYY-MM-DD`), `amount: str`, `destination_name: str | None`, and
  `category_name: str | None`. If `destination_name` or `category_name` is
  absent from the API response, then the system shall set the corresponding
  field to `None`.
- UC-006-4: The system shall export `TransactionRead` from
  `firefly_python_api`.
- UC-006-5: The system shall include `source_name: str | None` and
  `source_id: str | None` fields in `TransactionRead`, representing the
  split's source account (the account funds are drawn from), needed by
  consumers to plan balance transfers ahead of recurring withdrawals. If
  `source_name` or `source_id` is absent from the API response, then the
  system shall set the corresponding field to `None`, per the same rule as
  `destination_name` and `category_name` (UC-006-3).

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
- UC-007-2a: `create_bill(payload)` accepts a `BillPayload` `TypedDict` with
  required fields `name: str`, `amount_min: str`, `amount_max: str`,
  `date: str` (`YYYY-MM-DD`), `repeat_freq: str`, and `active: bool`.
  `repeat_freq` values accepted by the Firefly III API are `weekly`,
  `monthly`, `quarterly`, `half-year`, and `yearly`.
- UC-007-2b: The system shall send `repeat_freq` values to the Firefly III
  API without performing client-side validation, relying on the Firefly III
  API to reject invalid values (accepted values: `weekly`, `monthly`,
  `quarterly`, `half-year`, `yearly`).
- UC-007-3: The system shall make `BillPayload` importable from
  `firefly_python_api`.
- UC-007-4: When `create_bill()` raises `FireflyConnectionError` because the
  response status was outside 200 and 201, the system shall attach
  `status_code: int` to the raised exception, and, when the response body is
  valid JSON, shall attach `response_body: dict[str, Any]` to the raised
  exception, defaulting both attributes to `None` when unavailable (for
  example, for a network-level failure with no response).

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.
- The system shall preserve existing behavior for existing callers of
  `create_bill()`, `create_transaction()`, and any `_get`/`_post` caller
  when the `status_code` and `response_body` attributes (UC-007-4) are added
  to the exception raised by `create_bill()`; no other behavioral change
  shall be introduced.

## REQ-008 Progress Reporting for Paginated Fetches

**As a** consumer application (e.g. firefly-bills-analyzer),
**I want** to be notified after each page of a paginated fetch completes,
**so that** I can render a progress indicator (e.g. a CLI progress bar) without
this library taking a dependency on any particular UI/progress-bar toolkit.

### Use cases

- UC-008-1: `get_withdrawal_transactions(start, end, on_page=None)` accepts an
  optional `on_page` callback: `Callable[[int, int], None] | None`. When
  provided, the system shall invoke `on_page(page, total_pages)` once per
  page, immediately after that page's data has been fetched and parsed
  (`page` is the 1-indexed page just completed; `total_pages` is read from
  that response's `meta.pagination.total_pages`).
- UC-008-2: When `on_page` is `None` (the default), the system's behavior
  shall be unchanged from today: no callback is invoked, and the return
  value of `get_withdrawal_transactions()` is unaffected either way.
- UC-008-3: The system shall invoke `on_page` synchronously in the same
  thread as the fetch loop, after each page, in page order; an exception
  raised by `on_page` shall propagate to the caller of
  `get_withdrawal_transactions()` (the library shall not swallow it).

### Constraints

- No new runtime dependencies — `on_page` is a plain callable; this library
  shall not import or depend on `tqdm` or any other progress-bar package.
- Fully backward compatible: existing callers that do not pass `on_page` see
  no behavioral change.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.

## REQ-009 Account Opening Balance

**As a** consumer application (e.g. firefly-bank-importer),
**I want** a method to set an account's opening balance and opening balance date via `FireflyClient`,
**so that** I can establish a correct starting point for balance calculations after clearing
and re-importing transaction history, without reimplementing the HTTP call.

### Use cases

- UC-009-1: `set_opening_balance(account_id, balance, date)` — `PUT /api/v1/accounts/{id}`
  with body `{"opening_balance": balance, "opening_balance_date": date}`; treats HTTP 200
  as success; raises `FireflyConnectionError` on any other status code.
- UC-009-2: `balance` is a `str` (Firefly III represents monetary amounts as decimal
  strings, consistent with `TransactionPayload.amount`); `date` is a `str` in
  `YYYY-MM-DD` format.
- UC-009-3: When `set_opening_balance()` raises `FireflyConnectionError` because the
  response status was not 200, the system shall attach `status_code: int` to the raised
  exception, and, when the response body is valid JSON, shall attach
  `response_body: dict[str, Any]` to the raised exception, defaulting both attributes to
  `None` when unavailable — mirroring the pattern established for `create_bill()`
  (UC-007-4).
- UC-009-4: The system shall add a `_put_expect` internal helper mirroring
  `_post_expect` (same request/error-attachment behavior, using `session.put` instead of
  `session.post`), used by `set_opening_balance` and available for future PUT-based
  methods.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.

## REQ-010 Account Opening Balance Read

**As a** consumer application (e.g. firefly-bank-importer),
**I want** a method to read an account's current opening balance and opening balance date via
`FireflyClient`,
**so that** I can decide whether `set_opening_balance()` needs to be called at all before
clearing and re-importing transaction history, without reimplementing the HTTP call.

### Use cases

- UC-010-1: `get_opening_balance(account_id)` — `GET /api/v1/accounts/{id}`; on success,
  returns an `OpeningBalance` (`TypedDict`) with `balance: str | None` and
  `date: str | None`, read from the response's `attributes.opening_balance` and
  `attributes.opening_balance_date`, defaulting to `None` when the account has no
  opening balance set.
- UC-010-2: Uses the existing `_get` helper (same behavior as `get_asset_accounts()` and
  `get_latest_transaction_date()`); raises `FireflyConnectionError` on any network error
  or non-2xx HTTP response, including a 404 for an unknown `account_id`.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.

## REQ-011 Deposit Transaction Fetching

**As a** consumer application (e.g. firefly-bills-analyzer),
**I want** a method that returns all deposit transactions in a date range as typed data,
**so that** I can analyze incoming money — recurring salary payments in particular —
with the same pagination handling and split flattening the withdrawal side already
gets, instead of reimplementing them for the opposite transaction direction.

### Use cases

- UC-011-1: `get_deposit_transactions(start, end, on_page=None)` — paginated
  `GET /api/v1/transactions?type=deposit&start=YYYY-MM-DD&end=YYYY-MM-DD&page=N`;
  follows all pages until `total_pages` is reached; returns `list[TransactionRead]`.
- UC-011-2: When a Firefly III transaction object returned by
  `get_deposit_transactions()` contains multiple splits under
  `attributes.transactions`, the system shall flatten each split into its own
  `TransactionRead` entry, by the same rule as UC-006-2.
- UC-011-3: The system shall represent each deposit split with the existing
  `TransactionRead` `TypedDict` and shall not introduce a separate type. The
  fields carry the same API values as on the withdrawal side, with the account
  roles reversed by Firefly III itself: for a deposit, `source_name` is the
  revenue account the money came from (e.g. an employer) and
  `destination_name` is the asset account it landed in. Absent fields are set
  to `None`, per UC-006-3 and UC-006-5.
- UC-011-4: The system shall accept the optional `on_page(page, total_pages)`
  callback with the same semantics as REQ-008 defines for
  `get_withdrawal_transactions()`: invoked after each page has been fetched and
  parsed, with exceptions propagating to the caller and stopping further page
  fetches.
- UC-011-5: The system shall not return transactions of type `transfer`.
  Firefly III types a movement between two of the user's own asset accounts as
  `transfer`, not as a deposit, so the `type=deposit` filter excludes them at
  the API. Consumers may therefore treat every returned record as money
  entering the household from outside it.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.
- Pagination, split flattening, and `TransactionRead` construction shall be
  shared with `get_withdrawal_transactions()` rather than duplicated; the two
  methods differ only in the `type` query parameter.

## REQ-012 Transaction Tags

**As a** consumer application (e.g. firefly-bills-analyzer),
**I want** each transaction split to carry the tags the user applied to it,
**so that** I can let the user override a classification I derived from the
category, on individual transactions, without them having to restructure their
categories to express an exception.

### Use cases

- UC-012-1: The system shall include a `tags: list[str]` field in
  `TransactionRead`, holding the split's `attributes.transactions[].tags` value
  from the Firefly III response.
- UC-012-2: If the tags field is absent from the API response, or is `null`,
  then the system shall set `tags` to an empty list, rather than to `None`. A
  transaction with no tags and a transaction whose tags were not returned are
  the same thing to a consumer, and an empty list removes a null check from
  every call site.
- UC-012-3: The system shall populate `tags` identically for
  `get_withdrawal_transactions()` and `get_deposit_transactions()`, since both
  build their records through the same split-flattening helper.
- UC-012-4: The system shall preserve the tag strings as returned, without
  case folding, trimming, or sorting. Tag matching semantics belong to the
  consumer.

### Constraints

- No new runtime dependencies.
- `mypy --strict` must pass.
- Unit test coverage must not drop below baseline.
- Additive only: existing fields of `TransactionRead` are unchanged, and no
  existing method signature changes.
