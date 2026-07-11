# TASK-007 Expose status code and response body on FireflyConnectionError

## Status

done

## Requirements

**Binding:** REQ-007
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-006
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a consumer application (firefly-bills-analyzer, UC4/FR-05d), I want
`create_bill()`'s `FireflyConnectionError` to carry the failed response's
status code and body, so that I can distinguish a 422 "name already in use"
validation error from any other non-2xx failure without re-parsing HTTP
internals myself.

## Description

Add `status_code: int | None` and `response_body: dict[str, Any] | None`
attributes to `FireflyConnectionError` (`src/firefly_python_api/_exceptions.py`),
both defaulting to `None`. Populate them in `_post_expect` (used by
`create_bill`) when the response status is outside the expected set:
`status_code` from `response.status_code`; `response_body` from
`response.json()`, swallowed to `None` if the body isn't valid JSON.

Only `_post_expect` gains this behavior — `_get`, `_post`, and their callers
(`create_transaction`, all `get_*` methods) are unaffected, since no other
caller needs this per UC-007-4 and the constraint against changing existing
behavior.

Covers UC-007-4.

## Branch

**Branch name:** `task/007-expose-error-response-details`
**Switch/create:** `git checkout -b task/007-expose-error-response-details`
**Make target:** `make branch-task f=TASK-007`

## Acceptance criteria (Gherkin)

- [x] Scenario: 422 from create_bill carries status code and body
      Given `create_bill(payload)` is called and the API responds with HTTP 422
      and a JSON body containing a validation message
      When the call raises `FireflyConnectionError`
      Then `exc.status_code == 422` and `exc.response_body` equals the parsed
      JSON body

- [x] Scenario: Non-JSON error body does not raise a secondary exception
      Given `create_bill(payload)` is called and the API responds with a
      non-2xx status and a body that is not valid JSON
      When the call raises `FireflyConnectionError`
      Then `exc.status_code` is set and `exc.response_body` is `None`

- [x] Scenario: Network-level failure leaves both attributes None
      Given `create_bill(payload)` is called and the underlying HTTP request
      raises `requests.RequestException` before any response is received
      When the call raises `FireflyConnectionError`
      Then `exc.status_code is None` and `exc.response_body is None`

- [x] Scenario: Other non-2xx statuses also carry the attributes
      Given `create_bill(payload)` is called and the API responds with a
      status outside 200/201 that is not 422 (e.g. 500)
      When the call raises `FireflyConnectionError`
      Then `exc.status_code` matches the response status and `exc.response_body`
      is populated when the body is valid JSON

- [x] Scenario: Existing _get/_post callers are unaffected
      Given `create_transaction()` or any `get_*` method raises
      `FireflyConnectionError`
      Then `exc.status_code` and `exc.response_body` are both `None` (unchanged
      from prior behavior — these call sites are not touched by this task)

- [x] Scenario: Type checking and quality gates pass
      Given the completed implementation
      When `mypy --strict` is run on `src/`, and `make lint && make test` are run
      Then all pass and unit test coverage does not drop below the task-start
      baseline

## Out of scope

- Adding status_code/response_body to `_get`/`_post` or any of their callers.
- Any change to `create_bill`'s success-path behavior (200/201 handling).
- Parsing or interpreting `response_body` contents (e.g. checking for a
  specific validation message) — that's the caller's (firefly-bills-analyzer
  TASK-004) responsibility.

## Blockers

None.

## Completion

**Date:** 2026-07-11
**Summary:** Added `status_code: int | None` and `response_body: dict[str, Any] | None`
attributes to `FireflyConnectionError`, populated by `_post_expect` (used by `create_bill`)
whenever the response status falls outside the expected set — `status_code` from
`response.status_code`, `response_body` from `response.json()` (swallowed to `None` on a
non-JSON body). `_get`/`_post` and their callers (`create_transaction`, all `get_*` methods)
are untouched, so both attributes stay `None` there, matching prior behavior. 82 tests pass,
100% coverage on `src/`, `mypy --strict` and `make lint` clean.

**Workflow Guardian verification notes:** independently re-ran `make test`/`mypy --strict`/
`make lint` rather than trusting the reported figures at face value. Test Design Reviewer
scored the added test suite 8.2/10 (Farley Index) and flagged one real (non-cosmetic) gap:
the already-checked acceptance criterion "existing `_get`/`_post` callers are unaffected" was
only verified for the `_get` path (via `get_bills()`); the `_post` path (`create_transaction()`)
had no equivalent regression test. Added `test_post_caller_leaves_attributes_none` (renamed
the existing test to `test_get_caller_leaves_attributes_none` for symmetry) to close the gap
before accepting the criterion as verified — 82 tests total (was 81), still 100% coverage. Two
other reviewer findings (422/500 path redundancy, `ValueError` vs. real
`requests.JSONDecodeError` mock fidelity) were judged stylistic/non-blocking and left as-is.
**Files changed:**

- `src/firefly_python_api/_exceptions.py` — modified
- `src/firefly_python_api/_client.py` — modified
- `tests/test_api_methods.py` — modified
- `docs/REQUIREMENTS.md` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-007-expose-error-response-details.md` — modified

**Branch:** `git checkout task/007-expose-error-response-details`
**Stage:** `git add src/firefly_python_api/_exceptions.py src/firefly_python_api/_client.py tests/test_api_methods.py docs/REQUIREMENTS.md CHANGELOG.md docs/tasks/TASK-007-expose-error-response-details.md`
**Commit:** `git commit -m "Expose status_code and response_body on FireflyConnectionError from create_bill (TASK-007)"`
