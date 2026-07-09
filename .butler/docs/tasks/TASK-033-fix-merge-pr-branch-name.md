# TASK-033 Fix merge-pr branch-name derivation

## Status

done

## Description

`merge-pr` (Makefile) currently recomputes the task branch name from the task
file's filename via a `sed` expression that produces `task/task-<NNN>-<slug>`
(a duplicated `task-` segment). The real branch convention, used everywhere
else (`branch-task`, `stage-task`, `commit-task`, `pr-task`, and
`butler_core.tasks.create_task`), is `task/<NNN>-<slug>`. Because of this
mismatch, `make merge-pr`/`make merge-current-task` always fail with
"No open PR for branch ..." even when a valid, mergeable PR exists.

Fix `merge-pr` to read the Branch name line directly from the task
file (the same source `branch-task` already uses for its Switch/create line)
instead of reconstructing the branch name from the filename.

Covers Requirement 10 from REQUIREMENTS_MCP.md.

**Depends on:** none

## Branch

**Branch name:** `task/033-fix-merge-pr-branch-name`
**Switch/create:** `git checkout -b task/033-fix-merge-pr-branch-name`
**Make target:** `make branch-task f=TASK-033`

## Acceptance criteria

- [x] `merge-pr` derives `BRANCH` from the task file's `**Branch name:**` line, not from the filename
- [x] `make merge-pr f=TASK-XXX` finds and squash-merges the correct open PR for a real task branch (e.g. `task/025-mcp-server`)
- [x] `make merge-current-task` (which delegates to `merge-pr`) works correctly when run from the task branch
- [x] Existing error messages ("No task file found matching '...'", "No open PR for branch ...", "PR #... not mergeable (...)") are unchanged
- [x] `make lint && make test` pass
- [x] (added mid-task, user-approved) `ruff-pre-commit` pinned to the same version as the project's `ruff` dependency, so `make lint` and the pre-commit hook agree

## Completion

**Date:** 2026-07-08
**Summary:** Fixed `merge-pr` in the Makefile to derive `BRANCH` by grepping the task file's
`**Branch name:**` line (same style already used by `branch-task` for its Switch/create line)
instead of reconstructing it from the task filename via a `sed` expression that produced
`task/task-<NNN>-<slug>` — a duplicated `task-` segment that never matched the real
`task/<NNN>-<slug>` convention, so `merge-pr`/`merge-current-task` always failed with "No open
PR for branch ...". Verified the fix by extracting the new grep/sed line in isolation against
real task files (TASK-025, TASK-023, TASK-033), confirming it produces the exact real branch
names, and against a malformed task file (no Branch name line), confirming the new "No
**Branch name:** line found" error path triggers correctly. Did not run a full live
`make merge-current-task` end-to-end (would require creating and merging a throwaway PR, a
hard-to-reverse GitHub-visible action outside this task's authorization) — the underlying branch
name computation, which is the only thing this fix changes, was verified directly instead;
the surrounding PR-lookup/mergeable-check/error-message logic is untouched from before. While
running `make lint` on this branch, discovered a second, unrelated pre-existing issue already on
`main` (introduced unknowingly by TASK-025): the `ruff-pre-commit` hook was pinned to `v0.11.0`
while the project's own `ruff` dev dependency resolves to `v0.15.20`; the two versions disagreed
on `mcp/server.py`'s import order, so a commit that passed the pre-commit hook still failed a
plain `make lint`. Per user's explicit approval, fixed in this same PR: pinned
`ruff-pre-commit` to `v0.15.20` and re-sorted `mcp/server.py`'s imports to match; confirmed
`uv run pre-commit run ruff --files mcp/server.py` and `make lint` now agree. Also fixed an
unrelated, pre-existing missing-trailing-newline in the untracked working-tree file
`REQUIREMENTS_BDD.md` (whitespace-only, not staged/committed) since `make lint`'s pymarkdown
step scans all `.md` files on disk regardless of git tracking status and was failing because of
it. Coverage unchanged: 34 tests, 99% (matches task-start baseline); `mcp/`'s own 12 tests still
pass.
**Files changed:**

- `Makefile` — modified
- `.pre-commit-config.yaml` — modified
- `mcp/server.py` — modified (import order only)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-033-fix-merge-pr-branch-name.md` — modified

**Branch:** `git checkout task/033-fix-merge-pr-branch-name`
**Stage:** `git add Makefile .pre-commit-config.yaml mcp/server.py CHANGELOG.md docs/tasks/TASK-033-fix-merge-pr-branch-name.md`
**Commit:** `git commit -m "Fix merge-pr branch-name derivation and pin ruff-pre-commit to match project ruff version"`
