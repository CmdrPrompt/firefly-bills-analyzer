# TASK-048 `butler-pull` deletes `.butler/templates` and `.butler/claude-agents` before a consumer can regenerate governance files

## Status

done

## Description

`make butler-pull` is:

```make
butler-pull:
    git subtree pull --prefix=.butler $(BUTLER_REMOTE) main --squash
    $(MAKE) butler-trim
```

`butler-trim` unconditionally deletes everything under `.butler/` except
`Makefile`:

```make
butler-trim:
    ...
    @find .butler/ -mindepth 1 -maxdepth 1 ! -name 'Makefile' -exec rm -rf {} +
    ...
```

`generate-governance-files` — the target that (re)writes a consumer project's
`CLAUDE.md`, `.github/copilot-instructions.md`, `.github/agents/*.agent.md`,
and `.claude/agents/*.agent.md` — reads its input from `.butler/templates/*.tmpl`
and copies from `.butler/claude-agents/*.agent.md`. Because `butler-trim` runs
automatically as the second step of `butler-pull`, both of those directories
are gone by the time `butler-pull` returns. A consumer who just pulled a new
butler version — specifically *to* pick up new or updated agent
templates — has no window in which to run `make generate-governance-files
FORCE=1` against the content they just fetched. The command that is named for
"getting updates" actively prevents applying the governance-file half of
those updates.

`butler-fetch` (`git subtree pull --squash` without the trim step) is the
only way to get updated templates into a runnable state, but this is
undocumented from `butler-pull`'s side: its `make help` line reads "Pull the
latest butler and trim — updates .butler/Makefile only", which reads as the
complete, intended way to update, not as a lossy operation that forecloses
part of the update. Nothing in `butler-pull`'s output warns the user that
`.butler/templates/` or `.butler/claude-agents/` changed upstream, or that
regenerating governance files is now-or-never.

**Reproduced today** in `firefly-bills-analyzer` (a consumer project): running
`make butler-pull` fetched a new butler version (`a2b4da5..c73e0c7`) that
added 3 new agent templates (`task-drafter`, `test-design-reviewer`,
`test-writer`) and substantially rewrote `workflow-guardian`, then
immediately deleted the only copies of those templates before the user could
regenerate anything. The only recovery path was manually restoring the
already-committed-but-working-tree-deleted files from the subtree-pull commit
(`git checkout HEAD -- .butler/claude-agents .butler/templates`), which
requires knowing the internal mechanics of `butler-trim` and is not
documented anywhere as a recovery step.

**Depends on:** none. Related to TASK-039 (Draft, "Conflict-free butler-pull
with CLI upgrade") but distinct: TASK-039's own acceptance criteria (R2)
require `.butler/` to end up trimmed-to-`Makefile`-only after `butler-pull`
regardless, so implementing TASK-039 as scoped would not fix this issue. Any
fix here should stay compatible with TASK-039's R1-R10 if both are
implemented.

## Branch

**Branch name:** `task/048-butler-pull-trims-before-governance-regen`
**Switch/create:** `git checkout -b task/048-butler-pull-trims-before-governance-regen`
**Make target:** `make branch-task f=TASK-048`

## Acceptance criteria

- [x] After `make butler-pull` completes in a consumer project where the pulled
      commit range touched `.butler/templates/` and/or `.butler/claude-agents/`,
      the user has a documented, supported way to run `make generate-governance-files
      FORCE=1` against the newly-pulled content — either because `butler-pull`
      no longer deletes those directories before the user has had a chance to
      regenerate, or because `butler-pull` performs the regeneration itself
      (behind a flag or automatically) before trimming.
- [x] If the fix relies on the user acting between fetch and trim, `butler-pull`'s
      output clearly states (a) whether templates/agent definitions changed in
      this pull, and (b) the exact command to run before the next trim.
- [x] `make help`'s description of `butler-pull` no longer implies it is a
      complete, non-lossy update path for governance files when it isn't (or,
      if fixed structurally, the description is updated to reflect the new
      guarantee).
- [x] A regression test simulates: `git subtree add` a fixture butler repo,
      `butler-trim`, commit; modify a file under the fixture's `templates/` or
      `claude-agents/`; run `make butler-pull`; assert that governance-file
      regeneration against the new content is possible (or was already
      performed), not silently foreclosed.
- [x] `CHANGELOG.md` updated with a behavior-first entry.
- [x] `make lint && make test` pass.

## Out of scope

- TASK-039's merge-conflict-on-repeat-pull and stale-CLI problems — separate,
  already-drafted task.
- Changing what `generate-governance-files` reads from or how it substitutes
  template variables.
- Retroactively fixing consumer projects that already hit this and manually
  recovered (e.g. `firefly-bills-analyzer`) — this task only fixes the
  `python-butler` tooling itself.

## Blockers

None.

## Completion

**Date:** 2026-07-11
**Summary:** `butler-pull` now diffs `.butler/templates/` and `.butler/claude-agents/`
between the pre- and post-pull HEAD; if either changed, it prints the changed
files and the exact follow-up commands and skips the automatic trim, instead
of deleting the new content immediately. A failed subtree pull (e.g. a merge
conflict) is also no longer followed by a trim. `make help` and the README's
update instructions were updated to describe this conditional behavior. Note:
fully regenerating governance files after *any* prior `butler-trim` still
requires every consumed template file to have changed in the same pull for
`git subtree pull` to avoid a modify/delete conflict on unchanged-but-deleted
paths — that deeper subtree-merge limitation is out of scope here and tracked
under TASK-039.
**Files changed:**

- `Makefile` — modified
- `src/butler_core/data/Makefile` — modified (kept byte-identical to `Makefile` per the TASK-045 drift regression test)
- `README.md` — modified (update instructions for the new conditional trim behavior)
- `CHANGELOG.md` — modified
- `REQUIREMENTS_BUTLER_PULL.md` — added
- `tests/test_butler_pull_governance_regen.py` — added
- `docs/tasks/TASK-048-butler-pull-trims-before-governance-regen.md` — modified

**Branch:** `git checkout task/048-butler-pull-trims-before-governance-regen`
**Stage:** `git add Makefile src/butler_core/data/Makefile README.md CHANGELOG.md REQUIREMENTS_BUTLER_PULL.md tests/test_butler_pull_governance_regen.py docs/tasks/TASK-048-butler-pull-trims-before-governance-regen.md`
**Commit:** `git commit -m "Fix butler-pull deleting templates/claude-agents before governance regen is possible (TASK-048)"`
