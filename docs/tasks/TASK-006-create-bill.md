# TASK-006 Create bill via API

## Status

done

## Requirements

**Binding:** REQ-007
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bills-analyzer), I want a method to
create a new bill via `FireflyClient`, so that I can programmatically
register recurring bills without duplicating HTTP calls.

## Description

Add `FireflyClient.create_bill(bill)` — a method that POSTs a new bill to
`POST /api/v1/bills`. This is the only write operation needed by
`firefly-bills-analyzer` (UC4) that is not yet exposed by the client.

A new `BillPayload` TypedDict is introduced for the input type, carrying the
fields the Firefly III API requires: `name`, `amount_min`, `amount_max`,
`date`, `repeat_freq`, `active`.

Error handling mirrors the create/POST pattern already established by
`FireflyClient.create_transaction()` (REQ-002 / UC-002-3, delivered in
TASK-002): HTTP 200 and 201 are treated as success, any other status raises
`FireflyConnectionError`. TASK-002 is already merged to `main`, so this is a
design precedent to follow, not a blocking dependency for this task.

## Branch

**Branch name:** `task/006-create-bill`
**Switch/create:** `git checkout -b task/006-create-bill`
**Make target:** `make branch-task f=TASK-006`

## Acceptance criteria (Gherkin)

Scenarios are inline (BDD-ABSENT) and lift-ready for `.feature` extraction if
BDD tooling is adopted later.

- [x] Scenario: Bill creation succeeds on HTTP 200
      Given a valid `BillPayload`
      When `create_bill(payload)` is called and the API responds with HTTP 200
      Then the call completes without raising an exception

- [x] Scenario: Bill creation succeeds on HTTP 201
      Given a valid `BillPayload`
      When `create_bill(payload)` is called and the API responds with HTTP 201
      Then the call completes without raising an exception

- [x] Scenario: Bill creation fails on duplicate bill name (422)
      Given a `BillPayload` whose `name` duplicates an existing bill
      When `create_bill(payload)` is called and the API responds with HTTP 422
      Then a `FireflyConnectionError` is raised

- [x] Scenario: Bill creation fails on any other non-success status
      Given a valid `BillPayload`
      When `create_bill(payload)` is called and the API responds with a status
      other than 200 or 201
      Then a `FireflyConnectionError` is raised

- [x] Scenario: Bill creation fails on a network/connection error
      Given a valid `BillPayload`
      When `create_bill(payload)` is called and the underlying HTTP request
      fails with a connection error
      Then a `FireflyConnectionError` is raised

- [x] Scenario: BillPayload defines the required fields
      Given the `BillPayload` `TypedDict` in `src/firefly_python_api/_types.py`
      Then it declares required fields `name: str`, `amount_min: str`,
      `amount_max: str`, `date: str` (`YYYY-MM-DD`), `repeat_freq: str`,
      `active: bool`

- [x] Scenario: repeat_freq is not validated client-side
      Given a `BillPayload` with any `repeat_freq` value
      When `create_bill(payload)` is called
      Then the client sends the value to the API without validating it against
      the accepted enum (`weekly`, `monthly`, `quarterly`, `half-year`,
      `yearly`); invalid values are rejected by the Firefly III API, not the
      client

- [x] Scenario: BillPayload is importable from the package
      Given the `firefly_python_api` package
      When `BillPayload` is imported from `firefly_python_api`
      Then the import succeeds

- [x] Scenario: Type checking and quality gates pass
      Given the completed implementation of `create_bill` and `BillPayload`
      When `mypy --strict` is run on `src/`, and `make lint && make test` are
      run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Bill update, delete, or single-bill read operations — only `get_bills()`
  (REQ-003 / UC-003-1) exists and is unaffected by this task.
- Client-side validation of `repeat_freq` values — per UC-007-2, invalid
  values are rejected by the Firefly III API, not the client.
- Any `BillPayload` field not listed in UC-007-2 (`name`, `amount_min`,
  `amount_max`, `date`, `repeat_freq`, `active`).

## Blockers

None.

## Completion

**Date:** 2026-07-10
**Summary:** Added `FireflyClient.create_bill(payload)` (`POST /api/v1/bills`, 200/201 success,
`FireflyConnectionError` otherwise) and the `BillPayload` TypedDict (`name`, `amount_min`,
`amount_max`, `date`, `repeat_freq`, `active`), exported from `firefly_python_api`. 76 tests pass,
100% coverage on `src/`, `mypy --strict` and `make lint` clean. `_post_expect` added as a
dedicated helper (distinct from the pre-existing `_post`) since this requirement needs
exactly HTTP 200/201 to count as success — `_post`'s `raise_for_status()` only rejects
4xx/5xx and would silently accept e.g. 204. Test Design Reviewer scored the added test
suite 7.9/10 (Farley Index); no correctness bugs found, only minor nits (some overlap
between the 201-success and request-shape tests, exact `assert_called_once_with` call-shape
coupling, no test locks down `_post`/`create_transaction` was left unaffected). Judged
non-blocking per the Test review gate (stylistic, not correctness) and left as-is.
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
