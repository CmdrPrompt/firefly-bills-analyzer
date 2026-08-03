# TASK-012 Add transaction listing and deletion to FireflyClient

## Status

done

## Requirements

**Binding:** REQ-002 (UC-002-4, UC-002-5)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bank-importer), I want to list all
transaction IDs for a given account and delete individual transactions by ID,
so that I can implement a "clear transactions for selected accounts" feature
to support reimporting bank data, without duplicating pagination and HTTP
error handling across projects.

## Description

Add two new methods to `FireflyClient` in `src/firefly_python_api/_client.py`:

```python
def get_transactions_for_account(self, account_id: str) -> list[str]:
```

Paginated `GET /api/v1/accounts/{account_id}/transactions`, following the same
pagination pattern already used by `get_asset_accounts()` (loop until
`page >= data["meta"]["pagination"]["total_pages"]`). Returns a flat list of
transaction ID strings (`data[i]["id"]`) across all pages. An account with no
transactions returns an empty list.

```python
def delete_transaction(self, transaction_id: str) -> None:
```

`DELETE /api/v1/transactions/{transaction_id}`. Treats HTTP 204 as success.
Raises `FireflyConnectionError` on any other status code, following the same
error-handling pattern as `_post_expect`/`create_transaction`.

## Branch

**Branch name:** `task/012-transaction-listing-and-deletion`
**Switch/create:** `git checkout -b task/012-transaction-listing-and-deletion`
**Make target:** `make branch-task f=TASK-012`

## Acceptance criteria (Gherkin)

- [x] Scenario: List transaction IDs across multiple pages (UC-002-4)
      Given a Firefly III account whose transactions span 3 pages
      When `get_transactions_for_account(account_id)` is called
      Then it returns a flat list of all transaction IDs from all 3 pages
      And the IDs appear in API response order

- [x] Scenario: Account with no transactions (UC-002-4)
      Given a Firefly III account with zero transactions
      When `get_transactions_for_account(account_id)` is called
      Then it returns an empty list

- [x] Scenario: Delete a transaction succeeds (UC-002-5)
      Given a transaction ID that exists
      When `delete_transaction(transaction_id)` is called
      And the API responds with HTTP 204
      Then no exception is raised

- [x] Scenario: Delete a transaction fails (UC-002-5)
      Given a transaction ID
      When `delete_transaction(transaction_id)` is called
      And the API responds with a non-204 status code
      Then `FireflyConnectionError` is raised with the status code and response body

- [x] Scenario: Type checking and test suite pass (constraints)
      When `mypy --strict` is run on `src/`
      Then it passes with no errors
      And when `make lint && make test` is run
      Then both succeed
      And unit test coverage does not drop below the baseline recorded at task start

## Out of scope

- Any bulk/global delete-all-transactions endpoint (`DELETE /api/v1/data/destroy`) —
  not needed since callers can already select accounts via
  `get_transactions_for_account` + `delete_transaction`.
- Confirmation prompts, dry-run behavior, or CLI/UX — that belongs to the
  consumer project (firefly-bank-importer).

## Blockers

None

## Completion

**Date:** 2026-07-20
**Summary:** Added `get_transactions_for_account(account_id)` (paginated GET, returns a flat list of transaction IDs across all pages) and `delete_transaction(transaction_id)` (DELETE, 204 = success, else `FireflyConnectionError`) to `FireflyClient`, backed by a new private `_delete_expect` helper mirroring the existing `_post_expect` pattern. Covered by 9 new tests (4 for listing, 5 for deletion). All 97 tests pass with 100% coverage (no regression from the 100%/88-test baseline). ruff check, ruff format --check, mypy --strict, bandit, and complexipy all pass cleanly; `make lint`'s `check-agents-sync` failure is pre-existing on `main` and unrelated to files touched by this task (verified: only CHANGELOG.md, this task file, `_client.py`, and `test_api_methods.py` are modified).
**Files changed:**
- `src/firefly_python_api/_client.py` - modified
- `tests/test_api_methods.py` - modified
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-012-transaction-listing-and-deletion.md` - modified
**Branch:** `git checkout task/012-transaction-listing-and-deletion`
**Stage:** `git add src/firefly_python_api/_client.py tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-012-transaction-listing-and-deletion.md`
**Commit:** `git commit -m "Add transaction listing and deletion to FireflyClient"`
