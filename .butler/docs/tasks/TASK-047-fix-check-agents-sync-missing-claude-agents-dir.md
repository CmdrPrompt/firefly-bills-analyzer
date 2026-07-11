# TASK-047 Fix check-agents-sync crashing in projects without a claude-agents/ dir

## Status

done

## Description

`check-agents-sync` (`Makefile`, added in TASK-028) diffs `claude-agents/*.agent.md`
against `.claude/agents/*.agent.md` and is wired into `make lint`. It was written
for **python-butler's own repo**, where `claude-agents/` is the distributable
source of agent templates. But `src/butler_core/data/Makefile` is a byte-identical
copy of the root `Makefile` (per TASK-045) that gets vendored into every adopting
project via `butler sync`/`.butler/Makefile` — and adopting projects have no
reason to keep a top-level `claude-agents/` directory at all; their agent
definitions live only in `.claude/agents/` (and, in some projects, `.github/agents/`).

When `claude-agents/` doesn't exist, the target's
`for f in claude-agents/*.agent.md; do ...; done` loop hits bash's default
(non-`nullglob`) behavior: the glob doesn't expand and the loop body runs once
with the literal string `f='claude-agents/*.agent.md'`. `basename` then yields
`*.agent.md`, the script checks for a literally-named file
`.claude/agents/*.agent.md`, doesn't find it, and reports a nonsensical error —
reproduced verbatim in `firefly-bills-analyzer` (a `butler`-managed downstream
project with no `claude-agents/` directory):

```text
check-agents-sync: '*.agent.md' exists in claude-agents/ but not in .claude/agents/
check-agents-sync: 'bug-triage.agent.md' exists in .claude/agents/ but not in claude-agents/
... (one line per real file in .claude/agents/)
claude-agents/ and .claude/agents/ must stay identical — sync the files above.
make: *** [check-agents-sync] Error 1
```

This makes `make lint` (and anything that depends on it) permanently and
unfixably broken for every adopting project that doesn't happen to maintain a
`claude-agents/` directory — there is no file the user can add or sync command
that resolves it, since the check's premise (that `claude-agents/` should exist
and mirror `.claude/agents/`) doesn't apply outside python-butler's own repo.

Fix `check-agents-sync` so it only runs its diff when `claude-agents/` exists,
and treat its absence as "nothing to check" rather than an error — projects
that don't use the `claude-agents/` distribution pattern shouldn't be forced
to adopt it just to get a working `make lint`. Apply the same fix to both
`Makefile` and `src/butler_core/data/Makefile` (kept identical, per the
existing drift regression test from TASK-045).

**Depends on:** none

## Branch

**Branch name:** `task/047-fix-check-agents-sync-missing-claude-agents-dir`
**Switch/create:** `git checkout -b task/047-fix-check-agents-sync-missing-claude-agents-dir`
**Make target:** `make branch-task f=TASK-047`

## Acceptance criteria

- [x] `check-agents-sync` exits 0 with no output when `claude-agents/` does not
      exist in the current working directory
- [x] `check-agents-sync`'s existing drift-detection behavior (missing on
      either side, or differing content) is unchanged when `claude-agents/`
      does exist — verified against python-butler's own repo, which still has
      a real `claude-agents/` directory to keep in sync
- [x] No more literal-glob-string false positives (e.g. `'*.agent.md' exists
      in claude-agents/ but not in .claude/agents/`) are possible regardless
      of shell glob settings
- [x] `src/butler_core/data/Makefile` is kept byte-identical to `Makefile`
      (verified by the existing drift regression test)
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-11
**Summary:** Guarded `check-agents-sync` with `[ -d claude-agents ] || exit 0`
so the diff loop never runs — and never hits bash's non-`nullglob` literal-glob
false positive — in projects without a `claude-agents/` directory, while
leaving existing drift-detection behavior untouched when the directory
exists. Applied identically to `Makefile` and `src/butler_core/data/Makefile`.
Added `tests/test_check_agents_sync.py` covering both the missing-directory
no-op case and the existing drift-detection scenarios (missing file on either
side, differing content, identical dirs), plus a check against the real repo.
**Files changed:**

- `Makefile` — modified
- `src/butler_core/data/Makefile` — modified
- `CHANGELOG.md` — modified
- `tests/test_check_agents_sync.py` — added
- `docs/tasks/TASK-047-fix-check-agents-sync-missing-claude-agents-dir.md` — modified

**Branch:** `git checkout task/047-fix-check-agents-sync-missing-claude-agents-dir`
**Stage:** `git add Makefile src/butler_core/data/Makefile CHANGELOG.md docs/tasks/TASK-047-fix-check-agents-sync-missing-claude-agents-dir.md`
**Commit:** `git commit -m "Make check-agents-sync a no-op when claude-agents/ doesn't exist (TASK-047)"`
