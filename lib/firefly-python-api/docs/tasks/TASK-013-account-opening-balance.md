# TASK-013 Account opening balance

## Status

done

## Requirements

**Binding:** REQ-009
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (e.g. firefly-bank-importer), I want a method to
set an account's opening balance and opening balance date via
`FireflyClient`, so that I can establish a correct starting point for balance
calculations after clearing and re-importing transaction history, without
reimplementing the HTTP call.

## Description

Add `FireflyClient.set_opening_balance(account_id, balance, date)` — a method
that PUTs `{"opening_balance": balance, "opening_balance_date": date}` to
`PUT /api/v1/accounts/{id}`.

No `_put`/PUT helper exists yet on `FireflyClient` (only `_get`, `_post`,
`_post_expect`, `_delete_expect`). Add a new `_put_expect` internal helper
mirroring `_post_expect`'s request/error-attachment behavior (accepts
`expected_statuses`, attaches `status_code` and, when parseable,
`response_body` to the raised `FireflyConnectionError`), but issuing
`session.put` instead of `session.post`. `set_opening_balance` treats HTTP
200 as the only success status.

Error handling mirrors the pattern established by `create_bill()`
(REQ-007 / UC-007-4, delivered in TASK-006): on failure, `status_code: int`
and (when the body is valid JSON) `response_body: dict[str, Any]` are
attached to the raised `FireflyConnectionError`, both defaulting to `None`
when unavailable.

## Branch

**Branch name:** `task/013-account-opening-balance`
**Switch/create:** `git checkout -b task/013-account-opening-balance`
**Make target:** `make branch-task f=TASK-013`

## Acceptance criteria (Gherkin)

Scenarios are inline (BDD-ABSENT) and lift-ready for `.feature` extraction if
BDD tooling is adopted later.

- [x] Scenario: Opening balance is set successfully on HTTP 200
      Given a valid account id, a balance string, and a date string
      When `set_opening_balance(account_id, balance, date)` is called and the
      API responds with HTTP 200
      Then the call completes without raising an exception
      And the request was a PUT to `/api/v1/accounts/{account_id}` with JSON
      body `{"opening_balance": balance, "opening_balance_date": date}`

- [x] Scenario: Opening balance update fails on any non-200 status
      Given a valid account id, balance, and date
      When `set_opening_balance(account_id, balance, date)` is called and the
      API responds with a status other than 200 (e.g. 422 or 404)
      Then a `FireflyConnectionError` is raised
      And the exception carries `status_code` equal to the response status,
      and `response_body` equal to the parsed JSON body when the body is
      valid JSON

- [x] Scenario: Opening balance update fails on a network/connection error
      Given a valid account id, balance, and date
      When `set_opening_balance(account_id, balance, date)` is called and the
      underlying HTTP request fails with a connection error
      Then a `FireflyConnectionError` is raised
      And the exception's `status_code` and `response_body` are `None`

- [x] Scenario: _put_expect helper is reusable and mirrors _post_expect
      Given the internal `_put_expect(endpoint, payload, expected_statuses)`
      helper on `FireflyClient`
      Then it issues `session.put(endpoint, json=payload)`, raises
      `FireflyConnectionError` when the response status is outside
      `expected_statuses`, and attaches `status_code`/`response_body` to the
      exception using the same logic as `_post_expect`

- [x] Scenario: Type checking and quality gates pass
      Given the completed implementation of `set_opening_balance` and
      `_put_expect`
      When `mypy --strict` is run on `src/`, and `make lint && make test` are
      run
      Then `mypy --strict` passes, `make lint && make test` pass, and unit
      test coverage does not drop below the task-start baseline

## Out of scope

- Reading the current opening balance (no `get`/read counterpart) — only the
  write path described in REQ-009 is in scope.
- Any other account field updates via PUT (e.g. renaming an account, changing
  account type) — only `opening_balance` and `opening_balance_date`.
- Client-side validation of `balance` or `date` format — per the pattern in
  UC-007-2b, invalid values are rejected by the Firefly III API, not the
  client.
- Consumer-side integration (firefly-bank-importer's own logic for deciding
  when to call this method during re-import) — tracked separately in that
  project's own requirements/task docs.

## Blockers

None.

## Completion

**Date:** 2026-07-20
**Summary:** Added `FireflyClient._put_expect` (mirrors `_post_expect`, using `session.put`) and `FireflyClient.set_opening_balance(account_id, balance, date)`, which PUTs `{"opening_balance": balance, "opening_balance_date": date}` to `/api/v1/accounts/{id}` and treats HTTP 200 as the only success status. Covered by 13 new tests (success, non-200 statuses with `status_code`/`response_body` attachment, non-JSON error bodies, connection errors, and the `_put_expect` helper directly). No integration test was added, matching the existing pattern for `create_bill()`/`delete_transaction()` — the integration suite documents "no write operations are performed" against the live Firefly III instance; confirmed with the user. All 110 tests pass with 100% coverage (no regression from the 100%/97-test baseline). ruff check, ruff format --check, mypy --strict, bandit, and complexipy all pass cleanly; `make lint`'s `check-agents-sync` failure is pre-existing on `main` and unrelated to files touched by this task.
**Files changed:**
- `src/firefly_python_api/_client.py` - modified
- `tests/test_api_methods.py` - modified
- `CHANGELOG.md` - modified
- `docs/REQUIREMENTS.md` - modified
- `docs/tasks/TASK-013-account-opening-balance.md` - modified
**Branch:** `git checkout task/013-account-opening-balance`
**Stage:** `git add src/firefly_python_api/_client.py tests/test_api_methods.py CHANGELOG.md docs/REQUIREMENTS.md docs/tasks/TASK-013-account-opening-balance.md`
**Commit:** `git commit -m "Add account opening balance support to FireflyClient"`
