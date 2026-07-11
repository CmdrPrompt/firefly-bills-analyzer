# TASK-008 Parametrize redundant post-expect status-code tests

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

As a maintainer of the test suite, I want the `_post_expect` non-2xx status
coverage expressed as one parametrized test instead of two near-identical
tests, so that the suite has less duplicate maintenance cost without losing
any acceptance-criteria coverage.

## Description

**Test quality improvement:** `test_422_carries_status_code_and_response_body`
(`tests/test_api_methods.py:539`) and `test_other_non_success_status_carries_attributes`
(`tests/test_api_methods.py:566`) exercise the exact same `_post_expect`
branch (`src/firefly_python_api/_client.py:102-110`) — the only difference
between them is the literal status code (422 vs 500) and body content passed
to the mock. They were written as two separate tests because they map to two
distinct Gherkin scenarios in TASK-007's acceptance criteria ("422 from
create_bill carries status code and body" and "Other non-2xx statuses also
carry the attributes"), but that mapping does not require two separate test
*methods* — a single `@pytest.mark.parametrize` test with one case per status
code preserves both scenarios' traceability while removing the duplicated
Arrange/Act/Assert structure.
**Property:** Necessary
**Current blended score:** 7.2
**Target score:** 8.5
**Evidence:** `tests/test_api_methods.py:539`, `tests/test_api_methods.py:566`

Source: Test Design Reviewer Farley Index report on TASK-007's added tests
(run 2026-07-11, scoped to `TestCreateBill`), Farley Index 8.9/10. This finding
was left as non-blocking by the prior Workflow Guardian verification pass and
is picked up here as a standalone task per user request.

## Branch

**Branch name:** `task/008-parametrize-post-expect-status-tests`
**Switch/create:** `git checkout -b task/008-parametrize-post-expect-status-tests`
**Make target:** `make branch-task f=TASK-008`

## Acceptance criteria

- [x] `test_422_carries_status_code_and_response_body` and
      `test_other_non_success_status_carries_attributes` are replaced by one
      `@pytest.mark.parametrize`-driven test over `(status_code, body)` pairs
      (at minimum 422 and 500), asserting `exc.status_code` and
      `exc.response_body` for each case
- [x] Both original scenarios remain traceable: the parametrize IDs or test
      name make it clear which case is the 422 duplicate-name scenario and
      which is the generic non-2xx scenario
- [x] No coverage of `_post_expect`'s status-mismatch branch is lost
- [x] Farley Index re-evaluated for the Necessary property on the affected
      tests — blended score does not decrease from 7.2
- [x] `make lint && make test` pass, `mypy --strict` passes, coverage does not
      drop below the task-start baseline
- [x] `CHANGELOG.md` updated

## Out of scope

- Any change to `_post_expect` or other production code — this is a
  test-only refactor with no behavior change.
- The other two Farley findings from the same report (First/TDD process note;
  `ValueError` vs. real `requests.exceptions.JSONDecodeError` mock fidelity —
  the latter is TASK-009).

## Blockers

None.

## Completion

**Date:** 2026-07-11
**Summary:** Merged `test_422_carries_status_code_and_response_body` and
`test_other_non_success_status_carries_attributes` into one
`test_non_success_status_carries_status_code_and_response_body`, parametrized over
`(status_code, body)` with `id="422-duplicate-name"` / `id="500-generic-non-2xx"` for
traceability. No production code changed. Implemented together with TASK-009 on a shared
branch/PR per user request. 82 tests pass (same count as baseline — two tests replaced by
one parametrized test with two cases), 100% coverage, `mypy --strict` and `make lint` clean.
Test Design Reviewer re-scored the affected test: Necessary 7.2 → 8.8 (target 8.5, met).
Reviewer also noted residual redundancy with two adjacent, out-of-scope tests
(`test_raises_on_duplicate_name_422`, `test_raises_on_other_non_success_status`) — left
alone per this task's explicit Out of scope.
**Files changed:**

- `tests/test_api_methods.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-008-parametrize-post-expect-status-tests.md` — modified

**Branch:** `git checkout task/008-parametrize-post-expect-status-tests`
**Stage:** `git add tests/test_api_methods.py CHANGELOG.md docs/tasks/TASK-008-parametrize-post-expect-status-tests.md`
**Commit:** `git commit -m "Parametrize redundant post-expect status-code tests (TASK-008)"`
