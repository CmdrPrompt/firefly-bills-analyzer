# TASK-053 `butler-trim` guards against un-regenerated content regardless of invocation path

## Status
done

## Requirements
**Binding:** Requirement 4 (REQUIREMENTS_BUTLER_PULL.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none (TASK-048 and TASK-051 already `done`; this closes a gap
their diff-based guard left open)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer project maintainer who just resolved a `git subtree pull`
merge conflict by hand (following `butler-pull`'s own recovery instructions)
and then run `make butler-trim` directly, I want `butler-trim` to refuse to
delete `.butler/templates/`, `.butler/claude-agents/`, or
`.butler/claude-skills/` while they still hold content I haven't regenerated
into my project, so that the protection TASK-048/TASK-051 built into
`butler-pull`'s happy path also covers the conflict-recovery path — the one
place it's currently silent.

## Description
`butler-pull`'s change-detection guard (Requirement 1/3, TASK-048/051) only
runs after a *successful* `git subtree pull`. `git subtree pull` conflicts
structurally whenever the pull touches a file that a prior `butler-trim`
already deleted locally (see TASK-039's Background) — not a rare edge case,
but the expected outcome of trimming at all. When it conflicts,
`butler-pull` exits early and prints:

```
✗ butler-pull failed (e.g. a merge conflict) — not trimming.
  Resolve the conflict, then run 'make butler-trim' yourself once done.
```

That instruction sends the user straight to the unguarded `butler-trim`
target, bypassing Requirement 1/3's protection entirely. The same applies to
any other direct `make butler-trim` invocation outside `butler-pull`.

**Reproduced today** in `firefly-bills-analyzer`: this exact sequence
happened — `butler-pull` hit modify/delete conflicts on previously-trimmed
files, the conflict was resolved manually, and `make butler-trim` was run
directly per the printed instructions. No warning fired at any point in that
sequence, because Requirement 1/3's guard is a pre/post-pull diff that never
executes on this path — it would have stayed silent even if the pull had
carried new `claude-agents/`/`claude-skills/` content.

Fix `butler-trim` itself to check, at the moment it runs, whether
`.butler/templates/`, `.butler/claude-agents/`, or `.butler/claude-skills/`
currently exist and are non-empty, and refuse to delete them without
`FORCE=1` if so. This is a direct, invocation-path-independent check (does
this content exist right now?) rather than a diff, so it protects every route
into `butler-trim`, not just the one `butler-pull` already covers.

## Branch
**Branch name:** `task/053-butler-trim-guards-unregenerated-content`
**Switch/create:** `git checkout -b task/053-butler-trim-guards-unregenerated-content`
**Make target:** `make branch-task f=TASK-053`

## Acceptance criteria (Gherkin)
- [x] Scenario: butler-trim refuses when templates/claude-agents/claude-skills
      are non-empty
      Given `.butler/claude-skills/` (or `.butler/templates/` or
      `.butler/claude-agents/`) exists and contains at least one file
      When `make butler-trim` runs without `FORCE=1`
      Then it exits non-zero, deletes nothing under `.butler/`, and prints
      which path triggered the guard plus the exact follow-up commands
      (`make generate-governance-files FORCE=1`, then `make butler-trim`)
- [x] Scenario: FORCE=1 bypasses the guard
      Given the same non-empty `.butler/claude-skills/` state as above
      When `make butler-trim FORCE=1` runs
      Then it trims `.butler/` down to `Makefile` exactly as it does today
- [x] Scenario: guard is a no-op when there is nothing to protect
      Given `.butler/templates/`, `.butler/claude-agents/`, and
      `.butler/claude-skills/` are all absent or empty
      When `make butler-trim` runs without `FORCE=1`
      Then it trims `.butler/` down to `Makefile` exactly as it does today
- [x] Scenario: post-conflict recovery path is now protected
      Given a `butler-pull` that failed with a merge conflict, manually
      resolved and committed, where the resulting `.butler/claude-skills/`
      is non-empty
      When the user follows `butler-pull`'s own failure message and runs
      `make butler-trim`
      Then the guard fires instead of silently trimming
- [x] Scenario: README documents the conflict-recovery path
      Given `README.md`'s "Keeping butler up to date" section
      When a user's `butler-pull` fails with a merge conflict
      Then the section documents that outcome explicitly: how to resolve the
      conflict, that `make butler-trim` is now guarded (not blindly safe to
      run), and what `FORCE=1` does — not just the happy-path
      `butler-check`/`butler-pull` two-liner it documents today

## Out of scope
- TASK-039's structural fix (avoiding the subtree-pull conflict in the first
  place). This task makes the conflict's *recovery path* safe; it does not
  eliminate the conflict.
- Changing what `generate-governance-files` reads from or how it substitutes
  template variables.
- Retroactively fixing consumer projects that already hit this and manually
  recovered (e.g. `firefly-bills-analyzer`).

## Blockers
- None

## Completion
**Date:** 2026-07-20
**Summary:** `make butler-trim` (and its synced copy at
`src/butler_core/data/Makefile`) now refuses to delete anything under
`.butler/` if `.butler/templates/`, `.butler/claude-agents/`, or
`.butler/claude-skills/` exist and are non-empty, unless `FORCE=1` is passed.
It prints which path(s) triggered the guard and the exact follow-up commands.
`butler-pull`'s diff-skip message now prints `make butler-trim FORCE=1` as
its second follow-up command. README.md documents the guard, adds a new
"If `git subtree pull` conflicts" subsection, and updates both "Adopting"
flows and "Regenerating governance files" to pass `FORCE=1`. Four new tests
in `TestButlerTrimGuardsUnregeneratedContent`
(tests/test_butler_pull_governance_regen.py) cover all four Gherkin
scenarios; existing tests updated to pass `FORCE=1` where now required.
Verified independently: `make lint` and `make test` both pass (172 tests,
99% coverage), the four new test names match the four scenarios, the guard
logic in both Makefile copies is byte-identical, and README's new
conflict-recovery subsection is present.
**Files changed:** Makefile, src/butler_core/data/Makefile, README.md,
CHANGELOG.md, tests/test_butler_pull_governance_regen.py,
REQUIREMENTS_BUTLER_PULL.md, docs/tasks/TASK-051-butler-pull-skills-sync-gap.md,
docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md,
docs/tasks/TASK-053-butler-trim-guards-unregenerated-content.md
**Branch:** task/053-butler-trim-guards-unregenerated-content
**Stage:** `git add Makefile src/butler_core/data/Makefile README.md CHANGELOG.md REQUIREMENTS_BUTLER_PULL.md docs/tasks/TASK-051-butler-pull-skills-sync-gap.md docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md tests/test_butler_pull_governance_regen.py docs/tasks/TASK-053-butler-trim-guards-unregenerated-content.md`
**Commit:** `git commit -m "fix(TASK-053): make butler-trim guard un-regenerated content on every invocation path"`
