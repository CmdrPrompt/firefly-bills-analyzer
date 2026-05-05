# TASK-006 Create bill via API

## Status

todo

## Description

Add `FireflyClient.create_bill(bill)` — a method that POSTs a new bill to
`POST /api/v1/bills`. This is the only write operation needed by
`firefly-bills-analyzer` (UC4) that is not yet exposed by the client.

A new `BillPayload` TypedDict is introduced for the input type, carrying the
fields the Firefly III API requires.

## Branch

**Branch name:** `task/006-create-bill`
**Switch/create:** `git checkout -b task/006-create-bill`
**Make target:** `make branch-task f=TASK-006`

## Acceptance criteria

- [ ] `src/firefly_python_api/_types.py` defines `BillPayload` as a `TypedDict`
      with required fields `name: str`, `amount_min: str`, `amount_max: str`,
      `date: str` (`YYYY-MM-DD`), `repeat_freq: str`, `active: bool`
- [ ] `BillPayload` is exported from `firefly_python_api.__init__`
- [ ] `FireflyClient.create_bill(bill: BillPayload) -> None` POSTs to
      `POST /api/v1/bills`; HTTP 200 and 201 are treated as success; any other
      status raises `FireflyConnectionError`
- [ ] `repeat_freq` accepted values match Firefly III's enum:
      `weekly`, `monthly`, `quarterly`, `half-year`, `yearly`
- [ ] `tests/test_api_methods.py` covers: successful creation (201), duplicate
      name (422 → `FireflyConnectionError`), and network error
- [ ] `tests/test_types.py` covers `BillPayload` construction
- [ ] `mypy --strict` passes on `src/`
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_python_api/_types.py` — modified (BillPayload added)
- `src/firefly_python_api/_client.py` — modified (create_bill added)
- `src/firefly_python_api/__init__.py` — modified (BillPayload exported)
- `tests/test_api_methods.py` — modified
- `tests/test_types.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-006-create-bill.md` — modified

**Branch:** `git checkout task/006-create-bill`
**Stage:** `git add src/firefly_python_api/_types.py src/firefly_python_api/_client.py src/firefly_python_api/__init__.py tests/test_api_methods.py tests/test_types.py CHANGELOG.md docs/tasks/TASK-006-create-bill.md`
**Commit:** `git commit -m "Add create_bill() and BillPayload type (TASK-006)"`
