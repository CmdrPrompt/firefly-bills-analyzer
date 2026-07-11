# TASK-009 Use the real JSON decode error in the non-JSON-body test

## Status

done

## Requirements

**Binding:** REQ-007
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-007
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer relying on the test suite as a regression safety net, I want
the "non-JSON error body" test to fail if `_post_expect`'s exception handling
stops matching what `requests` actually raises, so that the test can't pass
by accident against a narrower or differently-shaped exception type.

## Description

**Test quality improvement:** `test_non_json_error_body_leaves_response_body_none`
(`tests/test_api_methods.py:549`) mocks the failure via
`resp.json.side_effect = ValueError("not JSON")` (`tests/test_api_methods.py:553`).
In production, `requests.Response.json()` raises `requests.exceptions.JSONDecodeError`
(itself a `ValueError` subclass, wrapping `json.JSONDecodeError`), not a bare
`ValueError`. The `except ValueError:` clause in `_post_expect`
(`src/firefly_python_api/_client.py:105`) happens to catch both today, but the
test's fidelity to the real failure mode is weaker than it looks: a future
change that narrowed the except clause to something that still catches a bare
`ValueError` but not the real `requests` exception type would pass this test
while breaking in production.
**Property:** Maintainable
**Current blended score:** 8.2
**Target score:** 9.0
**Evidence:** `tests/test_api_methods.py:553`

Source: Test Design Reviewer Farley Index report on TASK-007's added tests
(run 2026-07-11, scoped to `TestCreateBill`), Farley Index 8.9/10. This finding
was left as non-blocking by the prior Workflow Guardian verification pass and
is picked up here as a standalone task per user request.

## Branch

**Branch name:** `task/009-real-json-decode-error-in-mock`
**Switch/create:** `git checkout -b task/009-real-json-decode-error-in-mock`
**Make target:** `make branch-task f=TASK-009`

## Acceptance criteria

- [x] `test_non_json_error_body_leaves_response_body_none` raises
      `requests.exceptions.JSONDecodeError` (constructed the way `requests`
      itself constructs it, or via `requests.models.Response.json()`'s real
      failure path if that is more direct) from the mocked `resp.json`
      instead of a bare `ValueError`
- [x] The test still asserts `exc.status_code` is set and `exc.response_body`
      is `None`
- [x] Farley Index re-evaluated for the Maintainable property on this test —
      blended score does not decrease from 8.2
- [x] `make lint && make test` pass, `mypy --strict` passes, coverage does not
      drop below the task-start baseline
- [x] `CHANGELOG.md` updated

## Out of scope

- Any change to `_post_expect`'s `except ValueError:` clause — it already
  correctly catches `requests.exceptions.JSONDecodeError` since that type is a
  `ValueError` subclass; this task only tightens the test double.
- The other Farley findings from the same report (TASK-008; the First/TDD
  process note, which needs no code change).

## Blockers

None.

## Completion

**Date:** 2026-07-11
**Summary:** `test_non_json_error_body_leaves_response_body_none` now raises the real
`requests.exceptions.JSONDecodeError("Expecting value", "not json", 0)` from the mocked
`resp.json`, instead of a bare `ValueError`. Confirmed via `JSONDecodeError.__mro__`
(installed `requests==2.34.2`) that it subclasses `json.decoder.JSONDecodeError` ->
`ValueError`, so `_post_expect`'s existing `except ValueError:` genuinely catches it —
no production code changed. Implemented together with TASK-008 on a shared branch/PR per
user request. 82 tests pass, 100% coverage, `mypy --strict` and `make lint` clean. Test
Design Reviewer re-scored the fixed test: Maintainable 8.2 → 9.3 (target 9.0, met) — the
test would now correctly fail if `_post_expect`'s except clause were narrowed to no longer
cover `requests`' real exception type, which the prior bare-`ValueError` mock could not
have caught.
**Files changed:**

- `tests/test_api_methods.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-009-real-json-decode-error-in-mock.md` — modified

**Branch:** `git checkout task/009-real-json-decode-error-in-mock`
**Stage:** `git add tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-009-real-json-decode-error-in-mock.md`
**Commit:** `git commit -m "Use the real JSONDecodeError in the non-JSON-body test (TASK-009)"`
