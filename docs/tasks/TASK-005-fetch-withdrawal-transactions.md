# TASK-005 Fetch withdrawal transactions for a date range

## Status

todo

## Requirements

**Binding:** REQ-006
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bills-analyzer), I want a method that
returns all withdrawal transactions in a date range as typed data, so that I
can analyze spending/recurring payments without reimplementing pagination or
Firefly III's split-transaction structure.

## Description

Add `FireflyClient.get_withdrawal_transactions(start, end)` — a paginated method
that returns all withdrawal transactions between two dates. This is the only method
needed by `firefly-bills-analyzer` (UC1) that is not yet exposed by the client.

The Firefly III endpoint is `GET /api/v1/transactions` with query parameters
`type=withdrawal`, `start=YYYY-MM-DD`, `end=YYYY-MM-DD`, and `page=N`.

A new `TransactionRead` TypedDict is introduced for the return type, carrying the
fields that the bills analyzer needs: `date`, `amount`, `destination_name`, and
`category_name`.

## Branch

**Branch name:** `task/005-fetch-withdrawal-transactions`
**Switch/create:** `git checkout -b task/005-fetch-withdrawal-transactions`
**Make target:** `make branch-task f=TASK-005`

## Acceptance criteria (Gherkin)

Scenarios are lift-ready for `.feature` extraction if BDD tooling is adopted later.

- [ ] Scenario: Fetch withdrawal transactions across multiple pages (UC-006-1)
      Given a date range `start` and `end` in `YYYY-MM-DD` format
      When `get_withdrawal_transactions(start, end)` is called
      Then it requests `GET /api/v1/transactions?type=withdrawal&start={start}&end={end}&page=N`
      And it follows all pages until `total_pages` is reached
      And it returns a `list[TransactionRead]`

- [ ] Scenario: Flatten multi-split transactions into individual entries (UC-006-2)
      Given a Firefly III transaction object whose `attributes.transactions` contains
      multiple splits
      When `get_withdrawal_transactions(start, end)` processes that transaction object
      Then each split is flattened into its own `TransactionRead` entry in the returned list

- [ ] Scenario: `TransactionRead` shape and date truncation (UC-006-3)
      Given a Firefly III API response containing a withdrawal transaction split with a
      full ISO-8601 datetime in its `date` field
      When that split is converted into a `TransactionRead`
      Then `TransactionRead` is a `TypedDict` with `date: str` truncated to `YYYY-MM-DD`
      And `amount: str`
      And `destination_name: str | None`
      And `category_name: str | None`

- [ ] Scenario: Default missing optional fields to None (UC-006-3)
      Given a Firefly III API response for a withdrawal transaction split where
      `destination_name` and/or `category_name` are absent
      When that split is converted into a `TransactionRead`
      Then the resulting `TransactionRead` has `destination_name` set to `None` for any
      absent `destination_name`
      And `category_name` set to `None` for any absent `category_name`

- [ ] Scenario: `TransactionRead` is exported from the package (UC-006-4)
      Given the `firefly_python_api` package
      When a consumer imports from `firefly_python_api`
      Then `TransactionRead` is importable from `firefly_python_api.__init__`

- [ ] Scenario: Type checking and test suite pass (constraints)
      Given the implementation of `TransactionRead` and `get_withdrawal_transactions`
      When `mypy --strict` is run on `src/`
      Then it passes with no errors
      And when `make lint && make test` is run
      Then both succeed
      And unit test coverage does not drop below the baseline recorded at task start

## Out of scope

- Filtering or fetching transactions of any type other than `withdrawal`.
- Any write/create/update/delete operations on transactions.
- Support for transaction types other than withdrawal (e.g. deposit, transfer)
  in this method's return set.

## Blockers

None

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_python_api/_types.py` — modified (TransactionRead added)
- `src/firefly_python_api/_client.py` — modified (get_withdrawal_transactions added)
- `src/firefly_python_api/__init__.py` — modified (TransactionRead exported)
- `tests/test_api_methods.py` — modified (new tests)
- `tests/test_types.py` — modified (TransactionRead tests)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-005-fetch-withdrawal-transactions.md` — modified

**Branch:** `git checkout task/005-fetch-withdrawal-transactions`
**Stage:** `git add src/firefly_python_api/_types.py src/firefly_python_api/_client.py src/firefly_python_api/__init__.py tests/test_api_methods.py tests/test_types.py CHANGELOG.md docs/tasks/TASK-005-fetch-withdrawal-transactions.md`
**Commit:** `git commit -m "Add get_withdrawal_transactions() and TransactionRead type (TASK-005)"`
