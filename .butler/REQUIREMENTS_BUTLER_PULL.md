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

This document is scoped to TASK-048, TASK-051, and TASK-053. It does not
attempt to resolve TASK-039 (Draft) — repeat-pull merge conflicts and
stale-CLI drift — but the requirements below are written so they stay
compatible with TASK-039 R1–R10 if that task is implemented later (in
particular, TASK-039 R2's requirement that `.butler/` end up
trimmed-to-`Makefile`-only is treated as "eventually", not "as the
unconditional last step of every `butler-pull` invocation").

Requirement 4 covers a gap left open by Requirement 1/3: their change-detection
diff only runs inside a *successful* `git subtree pull`. When that step itself
conflicts — which it structurally will, per TASK-039's Background, on any
project that has trimmed and where the pull touches a previously-trimmed
file — `butler-pull` exits before the diff-and-defer logic ever executes, and
its own failure message tells the user to run `make butler-trim` directly,
bypassing Requirement 1/3's protection entirely.

## Goals

1. Give a consumer project a documented, supported way to run
   `make generate-governance-files FORCE=1` against content freshly pulled by
   `butler-pull`, before it is trimmed away.
2. Make it obvious, from `butler-pull`'s own output, whether this particular
   pull touched `.butler/templates/` or `.butler/claude-agents/`, and if so,
   exactly what command to run next.
3. Correct `make help`'s description of `butler-pull` so it no longer implies
   a guarantee it doesn't provide.
4. Make `butler-trim` itself safe to run — not just the automatic trim step
   inside a successful `butler-pull` — and document the conflict-recovery
   path (where a user is told to run `butler-trim` directly) in the README
   instead of leaving it unstated.

## Non-goals

- Fixing TASK-039's merge-conflict-on-repeat-pull or stale-CLI problems.
- Changing what `generate-governance-files` reads from, or how it
  substitutes template variables.
- Retroactively fixing consumer projects that already hit this and manually
  recovered (e.g. `firefly-bills-analyzer`).

## Scoped paths

The requirements below track three consumer-facing content directories under
`.butler/` — collectively "the scoped paths" — for change-detection,
generation, and trim-guard purposes:

- `.butler/templates/`
- `.butler/claude-agents/`
- `.butler/claude-skills/`

Any requirement below that refers to "the scoped paths" means exactly this
list.

## Requirement 1: `butler-pull` detects template/agent changes and defers trim

**Description:** `butler-pull` MUST compare the set of files under the
scoped paths (see "Scoped paths" above) before and after the
`git subtree pull` step (e.g. via `git diff --name-only` between the
previous and new HEAD, scoped to those paths).

- If none of the scoped paths changed, `butler-pull` MUST behave exactly as
  it does today: run the subtree pull, then immediately run `butler-trim`.
- If any of the scoped paths changed, `butler-pull` MUST **skip** the
  automatic `butler-trim` step for this invocation, and instead print a
  message that: (a) states which of the scoped paths changed in this pull,
  and (b) gives the exact next commands to run
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

## Requirement 3: `claude-skills`/`claude-agents` change-detection and generation are symmetric

**Description:** TASK-050 added a second consumer-facing content type,
`.butler/claude-skills/` (mirrored into `.claude/skills/` in a consumer
project), following the same shape as `.butler/claude-agents/` — it is one
of the scoped paths (see "Scoped paths" above). `generate-governance-files`
was never updated to treat it the same way as `claude-agents/`:

- `butler-pull`'s change-detection diff (Requirement 1) already covers this
  content type, since it diffs the full set of scoped paths.
- `generate-governance-files` MUST copy `.butler/claude-skills/*/SKILL.md`
  into a consumer project's `.claude/skills/`, mirroring the existing
  `cp .butler/claude-agents/*.agent.md .claude/agents/` step. Without this,
  there is no supported path — not even a manual one — for a consumer to
  ever receive skill files; today they can only be inspected via
  `git subtree`/git-log archaeology before the next trim deletes them.

**Reproduced today** in `firefly-bills-analyzer`: `make butler-pull` fetched
the TASK-050 skills content (`.butler/claude-skills/*`,
`.butler/.claude/skills/*`), the pull's change-detection did not flag it
(only `templates`/`claude-agents` are scoped), so `butler-trim` ran
immediately and deleted the only copies before `generate-governance-files`
could have copied them out even if the copy step existed.

**Use case:**

```bash
$ make butler-pull
# subtree pull runs, only .butler/claude-skills/ changed...
⚠ .butler/claude-skills/ changed in this pull.
  Governance files (.claude/skills/) may be out of date.
  Run this before the next trim:
    make generate-governance-files FORCE=1
    make butler-trim
```

## Requirement 4: `butler-trim` itself refuses to discard un-regenerated content

**Description:** Requirement 1 and Requirement 3's protection (defer the
automatic trim, warn, tell the user what to run) only fires on the
*automatic* trim step inside a successful `butler-pull`. It does not apply
when `butler-trim` is invoked any other way, in particular:

- After a `git subtree pull` merge conflict, where `butler-pull`'s own
  failure message ("Resolve the conflict, then run `make butler-trim`
  yourself once done.") sends the user straight to the unguarded target.
- Any direct `make butler-trim` invocation, by a human or an agent, run
  outside of `butler-pull` (e.g. while manually resolving a merge).

`butler-trim` MUST NOT rely on being called only from within `butler-pull` to
stay safe. Before deleting anything, it MUST check the *current*
working-tree state of the scoped paths (see "Scoped paths" above) — if any
of them exist and are non-empty, that is itself evidence of content that has
not yet been regenerated into the consumer project (a bare `make
butler-trim` cannot tell whether `generate-governance-files` already ran
against it, but existence of still-populated content is the same signal
Requirement 1/3 already act on, just observed directly instead of via a
pre/post-pull diff).

- If none of the scoped paths exist or are all empty, `butler-trim` MUST
  behave exactly as it does today.
- If any of the scoped paths exist and are non-empty, `butler-trim` MUST
  abort without deleting anything, print which path(s) triggered the guard,
  and print the exact commands to run first
  (`make generate-governance-files FORCE=1`, then `make butler-trim`).
- The guard MUST be bypassable with an explicit `FORCE=1` (mirroring the
  `butler-uninstall` convention elsewhere in this Makefile), for the rare
  case where a consumer genuinely wants to discard the content unread.
- The README's "Keeping butler up to date" section MUST document the
  conflict-recovery path explicitly: that a `git subtree pull` conflict is
  possible, how to resolve it, that the subsequent `make butler-trim` is now
  guarded rather than unconditionally safe, and what `FORCE=1` does — not
  just the happy-path `butler-check`/`butler-pull` sequence it documents
  today.

**Reproduced today** in `firefly-bills-analyzer`: a `butler-pull` failed with
modify/delete conflicts on files that a prior trim had already deleted
locally (`CHANGELOG.md`, `REQUIREMENTS_BUTLER_PULL.md`, and others — the
class of conflict TASK-039 exists to eliminate structurally). Following
`butler-pull`'s own recovery instructions, the conflict was resolved with a
plain `git merge --continue`-equivalent and `make butler-trim` was then run
directly, exactly as instructed. This trimmed the pull cleanly with no
warning, even though the same pull's merge commit brought no new
`claude-agents/`/`claude-skills/` content this time — but nothing about the
sequence of events would have caught it if it had, because the diff-based
guard in Requirement 1/3 never runs on this path at all.

**Use case:**

```bash
$ make butler-pull
# git subtree pull hits a modify/delete conflict and exits non-zero...
✗ butler-pull failed (e.g. a merge conflict) — not trimming.
  Resolve the conflict, then run 'make butler-trim' yourself once done.

# ... user resolves the conflict and commits the merge ...

$ make butler-trim
✗ Refusing to trim: .butler/claude-skills/ is not empty.
  Governance files (.claude/skills/) may be out of date. Run this first:
    make generate-governance-files FORCE=1
    make butler-trim

$ make butler-trim FORCE=1
Trimming .butler/ down to Makefile only ...
✓ Trim complete.
```

## Acceptance criteria (overall)

- [ ] `butler-pull` diffs the scoped paths (see "Scoped paths" above)
      between pre- and post-pull HEAD and skips the automatic `butler-trim`
      step when any of them changed, printing the exact follow-up commands.
- [ ] When none of those paths changed, `butler-pull`'s behavior is
      unchanged (fetch + trim in one step).
- [ ] `make help`'s `butler-pull` description matches the new conditional
      behavior.
- [ ] `generate-governance-files` copies `.butler/claude-skills/*/SKILL.md`
      into `.claude/skills/<name>/SKILL.md`, mirroring the
      `claude-agents/` → `.claude/agents/` copy.
- [ ] A regression test simulates: `git subtree add` a fixture butler repo,
      trim, commit; modify a file under one of the scoped paths; run
      `make butler-pull`; assert the trim was skipped, the warning was
      printed, and `generate-governance-files FORCE=1` afterwards succeeds
      against the newly-pulled content. A second fixture run with no scoped
      path changes asserts the trim ran automatically as before.
- [ ] `butler-trim`, invoked directly (not just via `butler-pull`), checks
      the current working-tree state of the scoped paths (see "Scoped
      paths" above) and aborts without deleting anything when any of them
      exist and are non-empty, printing which path(s) triggered the guard
      and the exact follow-up commands (`make generate-governance-files
      FORCE=1`, then `make butler-trim`).
- [ ] `make butler-trim FORCE=1` bypasses the guard and trims exactly as it
      does today, regardless of `.butler/` content.
- [ ] When the scoped paths (see "Scoped paths" above) are all absent or
      empty, a bare `make butler-trim` behaves exactly as it does today (no
      guard message).
- [ ] A regression test simulates the conflict-recovery path: a
      `butler-pull` merge conflict resolved and committed manually, leaving
      one of the scoped paths non-empty, followed by a direct `make
      butler-trim`; asserts the guard fires instead of silently trimming,
      and that `make butler-trim FORCE=1` then trims as before.
- [ ] The README's "Keeping butler up to date" section documents the
      conflict-recovery path: resolving a `git subtree pull` conflict, that
      `make butler-trim` is now guarded, and what `FORCE=1` does.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
