# TASK-051 `butler-pull` and `generate-governance-files` don't cover `claude-skills/`

## Status
done

## Requirements
**Binding:** Requirement 3 (REQUIREMENTS_BUTLER_PULL.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none (TASK-048 and TASK-050 both already `done`)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer project maintainer running `make butler-pull`, I want newly
published skills under `.butler/claude-skills/` to actually reach my
project's `.claude/skills/`, so that a butler update that adds or changes a
skill isn't silently deleted by the automatic trim before I ever see it.

## Description
TASK-050 introduced `.butler/claude-skills/` (mirrored `.claude/skills/`) as
a second consumer-facing content type alongside `.butler/claude-agents/`, but
did not extend `butler-pull`'s change-detection diff (added in TASK-048,
`REQUIREMENTS_BUTLER_PULL.md` Requirement 1) or `generate-governance-files`'s
copy step to cover it. As a result, skill updates are indistinguishable from
no-op pulls: `butler-pull` trims `.butler/` immediately, deleting the only
copy of any new/changed skill content, and even a manual
`make generate-governance-files FORCE=1` would not help because that target
never copies `claude-skills/` anywhere.

**Reproduced today** in `firefly-bills-analyzer`: `make butler-pull` pulled
TASK-050's five new skills (`changelog`, `characterization-tests`,
`commit-workflow`, `task-file-format`, `tdd-cycle`), the pull produced no
warning, `butler-trim` ran automatically, and the consumer project ended up
with no `.claude/skills/` directory at all — same failure mode TASK-048
already fixed for `claude-agents/`, just not extended to the sibling
`claude-skills/` path added one task later.

## Branch
**Branch name:** `task/051-butler-pull-skills-sync-gap`
**Switch/create:** `git checkout -b task/051-butler-pull-skills-sync-gap`
**Make target:** `make branch-task f=TASK-051`

## Acceptance criteria (Gherkin)
- [ ] Scenario: pull that only touches claude-skills defers trim
      Given a butler-pull whose commit range changes a file under
      `.butler/claude-skills/` but not `.butler/templates/` or
      `.butler/claude-agents/`
      When `make butler-pull` runs
      Then the automatic `butler-trim` step is skipped and a warning names
      `.butler/claude-skills/` and the exact follow-up commands
- [ ] Scenario: generate-governance-files copies skills
      Given `.butler/claude-skills/<name>/SKILL.md` exists after a
      `butler-fetch`
      When `make generate-governance-files FORCE=1` runs
      Then `.claude/skills/<name>/SKILL.md` exists in the consumer project
      and is byte-identical to the source
- [ ] Scenario: unaffected pulls behave as before
      Given a butler-pull that changes none of `.butler/templates/`,
      `.butler/claude-agents/`, or `.butler/claude-skills/`
      Then `butler-pull` trims automatically exactly as it does today

## Out of scope
- Retroactively fixing consumer projects that already hit this
  (`firefly-bills-analyzer` will resync manually after this ships).
- Any change to skill *content* or the `check-skills-sync` lint rule itself.
- TASK-039's broader repeat-pull/merge-conflict problem.

## Blockers
- None

## Completion
**Date:** 2026-07-20
**Summary:** Extended `butler-pull`'s pre/post-pull diff to also scope
`.butler/claude-skills/` (alongside the existing `templates/`/`claude-agents/`
scope), so a pull that only changes skills defers the automatic trim and
prints the same warning. Extended `generate-governance-files` to copy every
`.butler/claude-skills/*/SKILL.md` into `.claude/skills/<name>/SKILL.md`,
mirroring the existing `claude-agents/` -> `.claude/agents/` copy (guarded so
it no-ops cleanly when a consumer has no `claude-skills/` yet). Added two new
regression tests to `tests/test_butler_pull_governance_regen.py`
(`TestButlerPullSkipsTrimWhenSkillsChanged`,
`TestGenerateGovernanceFilesCopiesSkills`) and extended the existing
"unaffected pulls" test to also assert `claude-skills/` behavior. Re-synced
the bundled `src/butler_core/data/Makefile` copy with the root `Makefile`
(required by `tests/test_sync.py`'s drift check). Also closed a related gap
in `REQUIREMENTS_BUTLER_PULL.md`'s "Acceptance criteria (overall)" section,
which still only listed `templates/`/`claude-agents/` after Requirement 3 was
added — done ahead of this task, confirmed with the user, not itself part of
TASK-051's Gherkin scenarios. Also fixed a pre-existing, unrelated
`make lint` (pymarkdown MD009 trailing-spaces) failure in
`docs/tasks/TASK-049-document-manual-venv-activation.md`, at the user's
request, so `make lint` is fully green rather than reporting a known-ignored
failure on every run.

**Files changed:**

- `Makefile` - modified (scoped `claude-skills/` in `butler-pull`'s diff and
  warning; added the `claude-skills/*/SKILL.md` -> `.claude/skills/` copy
  loop to `generate-governance-files`; updated the `make help` line)
- `src/butler_core/data/Makefile` - modified (re-synced bundled copy)
- `tests/test_butler_pull_governance_regen.py` - modified (new skills
  regression tests, upstream fixture now includes `claude-skills/`)
- `REQUIREMENTS_BUTLER_PULL.md` - modified (Requirement 3 added; "overall"
  acceptance criteria closed for `claude-skills/`)
- `CHANGELOG.md` - modified (behavior-first entry under Fixed)
- `docs/tasks/TASK-049-document-manual-venv-activation.md` - modified
  (fixed pre-existing MD009 trailing-spaces lint failure, unrelated to
  TASK-051's scope but requested by the user so `make lint` is fully green)
- `docs/tasks/TASK-051-butler-pull-skills-sync-gap.md` - modified (this file)
- `docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md` - created
  (follow-up cleanup task, out of scope for TASK-051)
**Branch:** `git checkout task/051-butler-pull-skills-sync-gap`
**Stage:** `git add Makefile src/butler_core/data/Makefile tests/test_butler_pull_governance_regen.py REQUIREMENTS_BUTLER_PULL.md CHANGELOG.md docs/tasks/TASK-049-document-manual-venv-activation.md docs/tasks/TASK-051-butler-pull-skills-sync-gap.md docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md`
**Commit:** `git commit -m "Extend butler-pull change-detection and generate-governance-files to cover claude-skills/"`
