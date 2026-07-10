# TASK-029 Guardian subagent verification and worktree survival fixes

## Status

done

## Description

TASK-023 surfaced two subagent failure modes in the same session, filed as two
separate product bug reports:

1. **Worktree data loss.** Implementation Worker was told (in the calling
   prompt) not to commit inside its `isolation: "worktree"` worktree, on the
   assumption the Workflow Guardian would stage/commit after merging the
   worktree back. Since nothing was committed, the Agent tool tore down the
   worktree with no branch returned, silently discarding all file edits. The
   worker's own final report was also internally inconsistent (claimed "15
   tests written" but reported a test run of "92 passed", impossible given the
   repo's actual test count at the time), suggesting parts of its tool output
   were fabricated rather than real.

   Root cause, confirmed by reading `.claude/agents/implementation-worker.agent.md`:
   the agent's own instructions already say to commit via `make commit-current-task`
   — the calling prompt incorrectly overrode this. But `make commit-current-task`
   derives the task ID from the current branch name matching `task/<NNN>-...`,
   which an isolated worktree's branch does not necessarily match, so the
   worker's designed commit path is not safe to rely on as-is inside a worktree.

2. **Fabricated review.** Test Design Reviewer was asked to review two real
   files and returned a detailed report (line counts, function names, a git
   commit hash) that does not correspond to the actual repository state at
   all. `.claude/agents/test-design-reviewer.agent.md` instructs the reviewer
   to locate and read the test files itself ("Read every in-scope test file
   completely before scoring") — this is the mechanism that produced the
   fabricated result. A `run_in_background: false` call to this agent also
   returned early/asynchronously instead of synchronously, which may be
   related.

This task implements workarounds for both, plus a general verification layer
so a fabricated or lossy subagent report cannot silently pass as trusted work
in future tasks.

### Fix 1 — worktree commits must survive by construction

- Update `.claude/agents/implementation-worker.agent.md` (and its synced copy
  `claude-agents/implementation-worker.agent.md`, must stay identical per the
  TASK-028 sync rule) so that, when working inside an `isolation: "worktree"`
  context, the worker commits using `make commit-output f="<changed files>"
  m="wip(TASK-XXX): <short summary>"` instead of `make commit-current-task`
  (which requires a `task/<NNN>-...`-shaped current branch that a worktree
  does not have). This guarantees the worktree branch always has a commit
  before the agent finishes, so the Agent tool returns a branch instead of
  tearing down uncommitted work.
- Update `Makefile`'s `merge-worktree` target from `git merge $(b)` to
  `git merge --squash $(b)`, so the worker's wip commit(s) are squashed into
  staged changes (not an extra commit) when merged into the task branch.
  Workflow Guardian then runs the normal `make commit-current-task` to create
  the single real commit with the task file's actual commit message.
- Update `.claude/agents/workflow-guardian.agent.md` (and synced copy) step 7
  of the Operating Procedure to reflect the squash-merge and to state
  explicitly: if `make merge-worktree` reports no changes to squash, this
  means the worker produced no committed work — treat it as a failed worker
  run and fall back to implementing directly (this behavior is already
  documented but the squash-merge detail needs to be added).

### Fix 2 — reviewer receives file content directly, does not read it itself

- Update `.claude/agents/workflow-guardian.agent.md` (and synced copy) Test
  review gate / Operating Procedure step 11: before invoking Test Design
  Reviewer, Guardian reads the task's test file(s) and corresponding
  production file(s) itself and pastes their full literal content inline in
  the Test Design Reviewer prompt, instead of telling the reviewer to locate
  and read the files independently. This removes the tool-call path that
  produced fabricated content and makes the reviewer's input deterministic
  and verifiable by Guardian before it is even sent.
- Update `.claude/agents/test-design-reviewer.agent.md` (and synced copy)
  Step 1 ("Locate the test suite") to note that when file content is provided
  inline in the prompt, the reviewer should use that content directly rather
  than re-reading the files from disk.

### Fix 3 — general subagent report verification gate

Add a new mandatory gate to `.claude/agents/workflow-guardian.agent.md` (and
synced copy), applied after every Implementation Worker or Test Design
Reviewer report, before the report is trusted or acted on:

- Guardian independently re-verifies claims against ground truth using its
  own tool calls (not the subagent's self-reported numbers):
  - File existence and rough shape: `wc -l <file>` and `grep "^def "
    <file>` (or equivalent) compared against any file/function names the
    report claims.
  - Test count: `pytest --collect-only -q` compared against any test count
    the report claims.
  - Commit hash: `git log -1 --format=%H` on the relevant branch compared
    against any commit hash the report references.
  - Coverage/pass-fail: Guardian re-runs `make test` itself rather than
    trusting a reported coverage percentage or "N passed" line.
- If any claim does not match reality, the report is discarded, the mismatch
  is logged in the task's Completion summary, and Guardian falls back to
  performing the step itself (implementation or review) directly — the same
  fallback already documented for "Test Design Reviewer cannot be reached."
- As a soft heuristic (not a hard gate), Guardian notes when a subagent's
  reported token usage or duration seems implausibly low for the scope of
  work it claims to have done, as an early warning sign worth extra scrutiny.

**Out of scope for this task:** automating Fix 3's verification as a
`SubagentStop` hook that runs a validation script automatically. This is a
reasonable future enhancement but adds meaningful new scope (a validation
script, hook wiring in `.claude/settings.json`) beyond documenting and
enforcing the manual verification process in `workflow-guardian.agent.md`.
Flagged here so it isn't lost, not implemented in this task.

## Branch

**Branch name:** `task/029-guardian-subagent-verification`
**Switch/create:** `git checkout -b task/029-guardian-subagent-verification`
**Make target:** `make branch-task f=TASK-029`

## Acceptance criteria

- [x] `.claude/agents/implementation-worker.agent.md` instructs committing via
      `make commit-output f="..." m="wip(TASK-XXX): ..."` when in an isolated
      worktree, instead of `make commit-current-task`
- [x] `Makefile`'s `merge-worktree` target uses `git merge --squash $(b)`
      instead of `git merge $(b)`
- [x] `.claude/agents/workflow-guardian.agent.md` documents the squash-merge
      step and the "no changes to squash means the worker failed" fallback
- [x] `.claude/agents/workflow-guardian.agent.md` instructs Guardian to read
      test/production file content itself and paste it inline into the Test
      Design Reviewer prompt, instead of having the reviewer read files itself
- [x] `.claude/agents/test-design-reviewer.agent.md` accepts inline-provided
      file content as an alternative to reading files from disk
- [x] `.claude/agents/workflow-guardian.agent.md` documents the new subagent
      report verification gate (file/function existence, test count, commit
      hash, re-run coverage; discard and fall back on mismatch)
- [x] `claude-agents/*.agent.md` copies are byte-identical to their
      `.claude/agents/*.agent.md` counterparts (per TASK-028's sync rule);
      `make check-agents-sync` passes
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-08
**Summary:** Implemented directly in the main conversation (no Implementation Worker
sub-agent spawned for this task, given the lessons from TASK-023). Verified the
`merge-worktree` squash fix manually with a throwaway branch (`git merge --squash`
correctly stages changes without auto-committing). No new Python test files were
introduced (this task only changes agent prose and one Makefile target), so the Test
Design Reviewer gate did not apply. `make lint && make test` pass; coverage unchanged at
96% total (no Python behavior changed). `claude-agents/` copies synced and
`make check-agents-sync` passes.
**Files changed:**

- `.claude/agents/implementation-worker.agent.md` — modified
- `claude-agents/implementation-worker.agent.md` — modified
- `.claude/agents/workflow-guardian.agent.md` — modified
- `claude-agents/workflow-guardian.agent.md` — modified
- `.claude/agents/test-design-reviewer.agent.md` — modified
- `claude-agents/test-design-reviewer.agent.md` — modified
- `Makefile` — modified

**Branch:** `git checkout task/029-guardian-subagent-verification`
**Stage:** `git add .claude/agents/ claude-agents/ Makefile CHANGELOG.md docs/tasks/TASK-029-guardian-subagent-verification.md`
**Commit:** `git commit -m "Fix worktree commit survival and add subagent report verification gate to Workflow Guardian"`
