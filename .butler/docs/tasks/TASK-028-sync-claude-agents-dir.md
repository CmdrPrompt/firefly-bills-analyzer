# TASK-028 Sync claude-agents/ with .claude/agents/

## Status

done

## Description

`claude-agents/` is the distributable source of agent definitions copied into
adopting projects' `.claude/agents/` by `make generate-governance-files`
(`cp .butler/claude-agents/*.agent.md .claude/agents/`, see Makefile:381). The
two directories are meant to mirror each other (per TASK-021's completion
notes) but have drifted:

- `workflow-guardian.agent.md` differs: the `.claude/agents/` copy documents
  `isolation: "worktree"` for Implementation Worker plus the
  `make merge-worktree b=<branch>` follow-up step; the `claude-agents/` copy
  predates that change and doesn't mention it.
- `claude-agents/` is missing `test-design-reviewer.agent.md` and
  `test-writer.agent.md` entirely, both of which exist in `.claude/agents/`.

This task brings `claude-agents/` back in sync with `.claude/agents/` (the
latter is the actively-used, up-to-date copy) and adds a lint/CI-time check so
future drift is caught automatically instead of silently accumulating.

While updating `workflow-guardian.agent.md`, also add a new mandatory gate:
before staging any commit (`make stage-current-task` / `make stage-task`),
Workflow Guardian must have the Test Design Reviewer agent check the task's
test cases (against Dave Farley's 8 Properties of Good Tests) and address any
real findings. This closes a gap surfaced during TASK-022, where test review
happened only because the user asked for it after the commit had already been
made, rather than being an enforced step beforehand. Since this changes the
governance agent's own rules, the same change must be applied to both
`.claude/agents/workflow-guardian.agent.md` and
`claude-agents/workflow-guardian.agent.md` (they must stay identical per the
sync requirement above).

## Branch

**Branch name:** `task/028-sync-claude-agents-dir`
**Switch/create:** `git checkout -b task/028-sync-claude-agents-dir`
**Make target:** `make branch-task f=TASK-028`

## Acceptance criteria

- [x] `claude-agents/workflow-guardian.agent.md` is byte-identical to `.claude/agents/workflow-guardian.agent.md`
- [x] `claude-agents/test-design-reviewer.agent.md` and `claude-agents/test-writer.agent.md` are added, byte-identical to their `.claude/agents/` counterparts
- [x] Every other file in `claude-agents/` is verified identical to its `.claude/agents/` counterpart (no other drift found, or fixed if found)
- [x] A `make check-agents-sync` target (or equivalent) diffs `claude-agents/*.agent.md` against `.claude/agents/*.agent.md` and fails with a clear error if any file differs or is missing on either side
- [x] `check-agents-sync` is wired into `make lint` so drift is caught before merge
- [x] `workflow-guardian.agent.md` (both copies, kept identical) adds a mandatory gate: Test Design Reviewer must check the task's test cases against Dave Farley's 8 Properties before `make stage-current-task`/`make stage-task` is run, with any real findings addressed before staging
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Added a "Test review gate" rule to `workflow-guardian.agent.md` (both copies)
requiring a Test Design Reviewer pass over the task's tests, against Dave Farley's 8
Properties, before `make stage-current-task`/`stage-task`; updated the Operating Procedure
numbering to match. Synced `claude-agents/` to `.claude/agents/`: copied the updated
`workflow-guardian.agent.md`, and added the previously-missing `test-design-reviewer.agent.md`
and `test-writer.agent.md`. Discovered along the way that both source files in
`.claude/agents/` were missing a trailing newline (undetected because `.claude/` is excluded
from the pymarkdown scan in `make lint`) — fixed in the source files so the synced copies
pass pymarkdown's MD047 check. Added `make check-agents-sync`, wired into `make lint`, which
diffs every `*.agent.md` file between the two directories and fails with the specific
file(s) that differ or are missing on either side; verified it correctly fails on an
introduced diff and passes once synced.
**Files changed:**

- `.claude/agents/workflow-guardian.agent.md` — modified (pre-stage Test Design Reviewer gate)
- `.claude/agents/test-design-reviewer.agent.md` — modified (trailing newline)
- `.claude/agents/test-writer.agent.md` — modified (trailing newline)
- `claude-agents/workflow-guardian.agent.md` — synced + same gate added
- `claude-agents/test-design-reviewer.agent.md` — created
- `claude-agents/test-writer.agent.md` — created
- `Makefile` — modified (check-agents-sync target, wired into lint, added to .PHONY)

**Branch:** `git checkout task/028-sync-claude-agents-dir`
**Stage:** `git add .claude/agents/ claude-agents/ Makefile CHANGELOG.md docs/tasks/TASK-028-sync-claude-agents-dir.md`
**Commit:** `git commit -m "Sync claude-agents/ with .claude/agents/ and add drift check to make lint"`
