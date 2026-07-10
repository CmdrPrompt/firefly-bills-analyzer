# TASK-032 Add assertion messages to multi-assert CLI tests

## Status

done

## Description

**Test quality improvement:** Four tests in `tests/test_cli.py` make multiple assertions
with no failure message, so a failure does not immediately state which field diverged
without reading the test body: `test_prints_structured_task_data` (4 asserts),
`test_prints_checked_and_unchecked_acceptance_criteria` (2 asserts),
`test_prints_completion_date_and_summary_when_present` (2 asserts), and
`test_creates_new_task_file_and_prints_id` (2 asserts). Add an assertion message to each
`assert` in these tests stating what was expected.
**Property:** Understandable
**Current blended score:** 8.4
**Target score:** 9.0
**Evidence:** `tests/test_cli.py:49-52`, `tests/test_cli.py:68-69`,
`tests/test_cli.py:83-84`, `tests/test_cli.py:116-117`

Covers a Test Design Reviewer finding from the TASK-024 (`src/butler_cli/__main__.py`)
review.

## Branch

**Branch name:** `task/032-cli-multi-assert-failure-messages`
**Switch/create:** `git checkout -b task/032-cli-multi-assert-failure-messages`
**Make target:** `make branch-task f=TASK-032`

## Acceptance criteria

- [x] Identified tests refactored to address the finding
- [x] Farley Index re-evaluated — blended score for this property does not decrease
- [x] make lint && make test pass
- [x] CHANGELOG.md updated

## Completion

**Date:** 2026-07-08
**Summary:** Added a descriptive failure message to every `assert` in the four target tests
(names updated by TASK-031, which landed first: `test_prints_structured_task_data`,
`test_prints_acceptance_criteria_with_check_marks` (was
`test_prints_checked_and_unchecked_acceptance_criteria`),
`test_prints_completion_info_when_present` (was
`test_prints_completion_date_and_summary_when_present`), and
`test_creates_task_file_with_correct_metadata` (the 2-assert half of the test TASK-031 split
off from `test_creates_new_task_file_and_prints_id`)). Each message states the specific
field expected and echoes the actual captured value/output for debugging. Test Design
Reviewer scored Understandable at blended 9.0 (target 9.0, up from baseline 8.4) — target met.
**Files changed:**

- `tests/test_cli.py` — modified
- `docs/tasks/TASK-032-cli-multi-assert-failure-messages.md` — modified
- `CHANGELOG.md` — modified

**Branch:** `git checkout task/032-cli-multi-assert-failure-messages`
**Stage:** `git add tests/test_cli.py CHANGELOG.md`
**Commit:** `git commit -m "Add assertion messages to multi-assert CLI tests"`
