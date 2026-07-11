# TASK-022 butler_core tasks module

## Status

done

## Description

Implement `src/butler_core/tasks.py` providing a `Task` dataclass and all task
file operations: `read_task`, `list_tasks`, `create_task`, `check_criterion`,
`set_status`.

Covers Requirements 1–4 from REQUIREMENTS_MCP.md.

The parser must round-trip existing task files in `docs/tasks/` without
altering unrelated content. The writer must produce output compatible with the
existing `grep`/`sed` parsing in the Makefile (so `make branch-task`,
`stage-task`, `commit-task` keep working on tasks created via this module).

Tests must use Hypothesis for parsing edge cases as specified in the overall
acceptance criteria.

**Depends on:** TASK-021 (package scaffolding)

## Branch

**Branch name:** `task/022-butler-core-tasks-module`
**Switch/create:** `git checkout -b task/022-butler-core-tasks-module`
**Make target:** `make branch-task f=TASK-022`

## Acceptance criteria

- [x] `Task` dataclass has all fields from Req 1: `id`, `title`, `status`, `description`, `branch_name`, `switch_create_cmd`, `stage_cmd`, `commit_message`, `acceptance_criteria`, `completion`
- [x] `read_task("TASK-015", tasks_dir="docs/tasks")` returns correct structured data for an existing task file
- [x] `list_tasks(tasks_dir="docs/tasks", status="todo")` returns only tasks matching the filter
- [x] `create_task(title, description, tasks_dir)` allocates the next TASK-NNN number, writes a correctly formatted file
- [x] Files created by `create_task` work with `make branch-task`, `make stage-task`, `make commit-task`
- [x] `check_criterion("TASK-021", index=0, tasks_dir="docs/tasks")` toggles the checkbox
- [x] `set_status("TASK-021", "done", tasks_dir="docs/tasks")` updates the Status section
- [x] Hypothesis-based round-trip tests pass (parse → write → parse produces identical data)
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Implemented `Task`/`AcceptanceCriterion`/`Completion` dataclasses and
`read_task`, `list_tasks`, `create_task`, `check_criterion`, `set_status` in
`src/butler_core/tasks.py`, following TDD (tests written first in
`tests/test_tasks.py`). The parser handles both the current task-file template
and older completion-section variants (e.g. inline `Files changed:` lists,
missing blank lines) found in real files under `docs/tasks/`. Writer output for
the branch, stage, and commit metadata lines stays compatible with the
Makefile's `grep`/`sed` extraction. A Hypothesis test asserts
`parse_task(render_task(task)) == task` across randomized field values.
`check_criterion`/`set_status` rewrite only the targeted line, leaving the rest
of the file untouched. Coverage on the new module is 97%; overall project
coverage rose from the 0% baseline to 95%. `make lint && make test` pass.
**Files changed:**

- `src/butler_core/tasks.py` — created
- `tests/test_tasks.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-022-butler-core-tasks-module.md` — modified

**Branch:** `git checkout task/022-butler-core-tasks-module`
**Stage:** `git add src/butler_core/tasks.py tests/test_tasks.py CHANGELOG.md docs/tasks/TASK-022-butler-core-tasks-module.md`
**Commit:** `git commit -m "Use pytest.raises in tasks module tests (test-design review follow-up)"`
