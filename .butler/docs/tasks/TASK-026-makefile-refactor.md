# TASK-026 Makefile refactor

## Status

done

## Description

Refactor the existing Makefile targets (`branch-task`, `stage-task`,
`commit-task`, `pr-task`, `merge-pr` and their `-current-task` variants) to
delegate to `butler-cli` instead of inlining `grep`/`sed` parsing.

Covers Requirement 8 from REQUIREMENTS_MCP.md.

Target names, arguments (`f=TASK-XXX`), and all observable behavior must
remain identical. If `butler-cli` is not installed, targets must fail with a
clear error message pointing at how to install it — not a cryptic Python
traceback.

**Depends on:** TASK-024 (butler-cli fully implemented)

## Branch

**Branch name:** `task/026-makefile-refactor`
**Switch/create:** `git checkout -b task/026-makefile-refactor`
**Make target:** `make branch-task f=TASK-026`

## Acceptance criteria

- [x] `make branch-task f=TASK-021` delegates to `butler task branch TASK-021`
- [x] `make stage-task f=TASK-021` delegates to `butler task stage TASK-021`
- [x] `make commit-task f=TASK-021` delegates to `butler task commit TASK-021`
- [x] `make pr-task f=TASK-021` delegates to `butler task pr TASK-021`
- [x] `make merge-pr f=TASK-021` delegates to `butler task merge TASK-021`
- [x] All `-current-task` variants still derive TASK-NNN from branch name and delegate correctly
- [x] When `butler-cli` is not installed, each target prints a clear install instruction and exits 1
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Replaced the `grep`/`sed` task-file parsing in `branch-task`, `stage-task`,
`commit-task`, `pr-task`, and `merge-pr` with delegation to `butler --tasks-dir $(TASKS_DIR)
task <cmd> $(f)`, added a `check-butler` prerequisite target that fails with a clear install
instruction (not a traceback) when `butler` is not on PATH, and kept the `-current-task`
variants unchanged since they already derive `TASK-NNN` from the branch and call the
corresponding `-task` target. `pr-task` retains an explicit `butler task branch $(f)` call
before `butler task pr $(f)` because `open_pr_for` (unlike the old inline logic) does not
itself checkout/create the branch first. The Implementation Worker sub-agent spawned for this
task failed to commit (only read the Makefile, then stopped after ~4s with no worktree branch
returned) — per the Subagent verification gate this was treated as a failed run and the change
was implemented directly instead. No Python source or tests changed, so coverage stayed at the
task-start baseline (34 tests passed, 282 stmts / 4 miss / 99% total); no new test files exist
for this task so the Test Design Reviewer step does not apply.
**Files changed:**

- `Makefile` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-026-makefile-refactor.md` — modified

**Branch:** `git checkout task/026-makefile-refactor`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-026-makefile-refactor.md`
**Commit:** `git commit -m "Refactor Makefile task targets to delegate to butler-cli"`
