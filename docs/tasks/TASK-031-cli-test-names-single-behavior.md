# TASK-031 CLI test names should each state a single behavior claim

## Status

done

## Description

**Test quality improvement:** Several test names in `tests/test_cli.py` contain "and",
signalling a test that asserts more than one distinct behaviour (e.g.
`test_creates_new_task_file_and_prints_id`, `test_task_not_found_error_prints_message_and_returns_exit_code_1`,
`test_git_ops_error_prints_message_and_returns_exit_code_1`,
`test_check_index_error_prints_message_and_returns_exit_code_1`,
`test_prints_checked_and_unchecked_acceptance_criteria`,
`test_prints_completion_date_and_summary_when_present`). Where the two facts are genuinely
independent, split into two tests so a failure pinpoints which behaviour broke; where they
are one cohesive behaviour (e.g. "prints a clean error message AND exits 1" is arguably one
"fails cleanly" behaviour), rename to a single unifying name rather than splitting for its
own sake.
**Property:** Granular
**Current blended score:** 6.8
**Target score:** 7.8
**Evidence:** `tests/test_cli.py:71`, `tests/test_cli.py:97`, `tests/test_cli.py:184`,
`tests/test_cli.py:194`, `tests/test_cli.py:206`

Covers a Test Design Reviewer finding from the TASK-024 (`src/butler_cli/__main__.py`)
review.

## Branch

**Branch name:** `task/031-cli-test-names-single-behavior`
**Switch/create:** `git checkout -b task/031-cli-test-names-single-behavior`
**Make target:** `make branch-task f=TASK-031`

## Acceptance criteria

- [x] Identified tests refactored to address the finding
- [x] Farley Index re-evaluated — blended score for this property does not decrease
- [x] make lint && make test pass
- [x] CHANGELOG.md updated

## Completion

**Date:** 2026-07-08
**Summary:** Renamed 5 tests to single unifying names for cohesive two-fact behaviours
(`test_fails_cleanly_when_task_not_found`, `test_fails_cleanly_on_git_ops_error`,
`test_fails_cleanly_on_invalid_criterion_index`, `test_prints_acceptance_criteria_with_check_marks`,
`test_prints_completion_info_when_present`), and split `test_creates_new_task_file_and_prints_id`
into two independent tests (`test_prints_new_task_id` observing stdout only, and
`test_creates_task_file_with_correct_metadata` observing the persisted file via `read_task`
only) since printing the id and persisting the file are independent outcomes reached through
different mechanisms. Test count went from 34 to 35 (the one split). Test Design Reviewer
scored Granular at blended 7.8 (target 7.8, up from baseline 6.8) on first pass — a marginal
pass — and flagged one real residual finding: the split-off test still had "and" in its name
(`test_creates_task_file_with_given_title_and_description`), inconsistent with the refactor's
own stated policy since both fields are one cohesive persisted-metadata check. Renamed to
`test_creates_task_file_with_correct_metadata` before staging.
**Files changed:**

- `tests/test_cli.py` — modified
- `docs/tasks/TASK-031-cli-test-names-single-behavior.md` — modified
- `CHANGELOG.md` — modified

**Branch:** `git checkout task/031-cli-test-names-single-behavior`
**Stage:** `git add tests/test_cli.py CHANGELOG.md`
**Commit:** `git commit -m "Rename/split CLI test names so each states a single behavior claim"`
