# Requirements: `butler-pull` must not foreclose governance-file regeneration

## Context

`make butler-pull` runs `git subtree pull --prefix=.butler ... --squash`
immediately followed by `make butler-trim`, which deletes everything under
`.butler/` except `Makefile` — including `.butler/templates/` and
`.butler/claude-agents/`. `generate-governance-files` (the target that
(re)writes a consumer project's `CLAUDE.md`, `.github/copilot-instructions.md`,
`.github/agents/*.agent.md`, and `.claude/agents/*.agent.md`) reads its input
from exactly those two directories. Because the trim runs automatically as
part of `butler-pull`, a consumer who just pulled new or updated templates/
agent definitions has no window to regenerate governance files against the
content they just fetched — the only undocumented recovery is
`git checkout HEAD -- .butler/claude-agents .butler/templates` (TASK-048,
reproduced in `firefly-bills-analyzer`).

`make help` currently describes `butler-pull` as "Pull the latest butler and
trim — updates .butler/Makefile only", which reads as a complete, non-lossy
update path even though it silently forecloses regenerating governance files.

This document is scoped to TASK-048 only. It does not attempt to resolve
TASK-039 (Draft) — repeat-pull merge conflicts and stale-CLI drift — but the
requirement below is written so it stays compatible with TASK-039 R1–R10 if
that task is implemented later (in particular, TASK-039 R2's requirement that
`.butler/` end up trimmed-to-`Makefile`-only is treated as "eventually", not
"as the unconditional last step of every `butler-pull` invocation").

## Goals

1. Give a consumer project a documented, supported way to run
   `make generate-governance-files FORCE=1` against content freshly pulled by
   `butler-pull`, before it is trimmed away.
2. Make it obvious, from `butler-pull`'s own output, whether this particular
   pull touched `.butler/templates/` or `.butler/claude-agents/`, and if so,
   exactly what command to run next.
3. Correct `make help`'s description of `butler-pull` so it no longer implies
   a guarantee it doesn't provide.

## Non-goals

- Fixing TASK-039's merge-conflict-on-repeat-pull or stale-CLI problems.
- Changing what `generate-governance-files` reads from, or how it
  substitutes template variables.
- Retroactively fixing consumer projects that already hit this and manually
  recovered (e.g. `firefly-bills-analyzer`).

## Requirement 1: `butler-pull` detects template/agent changes and defers trim

**Description:** `butler-pull` MUST compare the set of files under
`.butler/templates/` and `.butler/claude-agents/` before and after the
`git subtree pull` step (e.g. via `git diff --name-only` between the previous
and new HEAD, scoped to those two paths).

- If neither path changed, `butler-pull` MUST behave exactly as it does
  today: run the subtree pull, then immediately run `butler-trim`.
- If either path changed, `butler-pull` MUST **skip** the automatic
  `butler-trim` step for this invocation, and instead print a message that:
  (a) states that `.butler/templates/` and/or `.butler/claude-agents/`
  changed in this pull, and (b) gives the exact next commands to run
  (`make generate-governance-files FORCE=1`, then `make butler-trim`).

**Use case:**

```bash
$ make butler-pull
# subtree pull runs...
⚠ .butler/templates/ and .butler/claude-agents/ changed in this pull.
  Governance files (CLAUDE.md, agent definitions) may be out of date.
  Run this before the next trim:
    make generate-governance-files FORCE=1
    make butler-trim
```

```bash
$ make butler-pull
# subtree pull runs, no template/agent changes detected...
Trimming .butler/ down to Makefile only ...
✓ Trim complete.
```

## Requirement 2: `make help` no longer overstates `butler-pull`'s guarantee

**Description:** The `make help` line for `butler-pull` MUST reflect the
behavior in Requirement 1 — that it trims automatically only when no
template/agent changes are detected, and otherwise pauses for the user to
regenerate governance files first — rather than unconditionally describing
it as "Pull the latest butler and trim."

## Acceptance criteria (overall)

- [ ] `butler-pull` diffs `.butler/templates/` and `.butler/claude-agents/`
      between pre- and post-pull HEAD and skips the automatic
      `butler-trim` step when either changed, printing the exact follow-up
      commands.
- [ ] When neither path changed, `butler-pull`'s behavior is unchanged
      (fetch + trim in one step).
- [ ] `make help`'s `butler-pull` description matches the new conditional
      behavior.
- [ ] A regression test simulates: `git subtree add` a fixture butler repo,
      trim, commit; modify a file under the fixture's `templates/` or
      `claude-agents/`; run `make butler-pull`; assert the trim was skipped,
      the warning was printed, and `generate-governance-files FORCE=1`
      afterwards succeeds against the newly-pulled content. A second fixture
      run with no template/agent changes asserts the trim ran automatically
      as before.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
