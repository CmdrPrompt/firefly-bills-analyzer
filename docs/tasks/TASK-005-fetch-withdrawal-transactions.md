# TASK-005 Fetch withdrawal transactions for a date range

## Status

todo

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

## Acceptance criteria

- [ ] `src/firefly_python_api/_types.py` defines `TransactionRead` as a `TypedDict`
      with at minimum: `date: str`, `amount: str`, `destination_name: str | None`,
      `category_name: str | None`
- [ ] `TransactionRead` is exported from `firefly_python_api.__init__`
- [ ] `FireflyClient.get_withdrawal_transactions(start: str, end: str)` calls
      `GET /api/v1/transactions?type=withdrawal&start={start}&end={end}&page=N`
      and follows all pages until `total_pages` is reached
- [ ] The method returns `list[TransactionRead]`, one entry per transaction split
      (each Firefly III transaction object may contain multiple splits in
      `attributes.transactions`; each split becomes one `TransactionRead`)
- [ ] `date` is truncated to `YYYY-MM-DD` (Firefly III returns full ISO-8601
      datetime strings)
- [ ] `destination_name` and `category_name` default to `None` when absent in the
      API response
- [ ] `TransactionRead` and `get_withdrawal_transactions` are covered by unit tests
      with mocked HTTP responses; coverage must not drop below the current baseline
- [ ] `mypy --strict` passes on `src/`
- [ ] `make lint && make test` pass

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
