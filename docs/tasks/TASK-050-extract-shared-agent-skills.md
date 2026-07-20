# TASK-050 Extract shared agent procedures into skills

## Status
done

## Requirements
**Binding:** Requirement 1 from REQUIREMENTS_AGENT_SKILLS.md
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of the agent definitions, I want the shared procedures
(commit workflow, task-file format, TDD cycle, changelog style,
characterization-test procedure) to live in one place instead of being
copy-pasted across ten agent files, so that a future change to any of them
only needs to be made once and cannot silently drift between agents.

## Description
Extracted the procedural text duplicated across `.claude/agents/*.agent.md`
(mirrored in `claude-agents/`) into five new skills under `.claude/skills/`
(mirrored in `claude-skills/`): `commit-workflow`, `task-file-format`,
`tdd-cycle`, `changelog`, `characterization-tests`. Every agent that used one
of these procedures now references the skill by name and loads it with the
`Skill` tool instead of restating it. Added `Skill` to each affected agent's
`tools:` list and to `VALID_TOOLS` in `scripts/validate_agents.py`. Added a
`check-skills-sync` Makefile target (wired into `make lint`) that fails if
`.claude/skills/` and `claude-skills/` drift apart, mirroring the existing
`check-agents-sync` target for the agents directories.

## Branch
**Branch name:** `task/050-extract-shared-agent-skills`
**Switch/create:** `git checkout -b task/050-extract-shared-agent-skills`
**Make target:** `make branch-task f=TASK-050`

## Acceptance criteria (Gherkin)
- [x] Scenario: Shared procedure lives in exactly one skill file
      Given a procedure referenced by two or more agent definitions
      When the agent files are inspected
      Then the full procedure text exists only in `.claude/skills/<name>/SKILL.md`
      and each referencing agent loads it via the `Skill` tool instead of
      restating it
- [x] Scenario: Skill directories are kept in sync
      Given `.claude/skills/` and `claude-skills/` both contain the five new
      skills
      When `make lint` is run
      Then `check-skills-sync` passes because the two directories are
      byte-identical, and would fail the build if they diverged
- [x] Scenario: `Skill` is a valid agent tool
      Given an agent's `tools:` list includes `Skill`
      When `uv run python scripts/validate_agents.py` is run
      Then validation passes because `"Skill"` is in `VALID_TOOLS`

## Out of scope
- Changing any agent's actual permissions, gating logic, or role boundaries
  beyond adding the `Skill` tool.
- Introducing new procedural rules — this is an extraction of existing,
  already-agreed rules, not new policy.

## Blockers
- None

## Completion
**Date:** 2026-07-20
**Summary:** Work was implemented directly rather than via the standard
`make branch-task` flow — this task file was written retroactively to
document and verify it. Note the branch-policy deviation: the changes were
made on `main` instead of a `task/050-...` branch. Requirement 1 in
REQUIREMENTS_AGENT_SKILLS.md was drafted and confirmed with the user before
this task file was written. Verified `make check-agents-sync`,
`make check-skills-sync`, `uv run python scripts/validate_agents.py`, and
`make lint` all pass; the five skill files are byte-identical between
`.claude/skills/` and `claude-skills/`.
**Files changed:**
- `REQUIREMENTS_AGENT_SKILLS.md` — created
- `docs/tasks/TASK-050-extract-shared-agent-skills.md` — created
- `.claude/skills/commit-workflow/SKILL.md` — created
- `.claude/skills/task-file-format/SKILL.md` — created
- `.claude/skills/tdd-cycle/SKILL.md` — created
- `.claude/skills/changelog/SKILL.md` — created
- `.claude/skills/characterization-tests/SKILL.md` — created
- `claude-skills/commit-workflow/SKILL.md` — created
- `claude-skills/task-file-format/SKILL.md` — created
- `claude-skills/tdd-cycle/SKILL.md` — created
- `claude-skills/changelog/SKILL.md` — created
- `claude-skills/characterization-tests/SKILL.md` — created
- `.claude/agents/*.agent.md` (all 10 files) — modified: added `Skill` to
  `tools:`, replaced inline procedure text with skill references
- `claude-agents/*.agent.md` (all 10 files) — modified, mirroring the above
- `Makefile` — modified: added `check-skills-sync`, wired into `lint`
- `scripts/validate_agents.py` — modified: added `"Skill"` to `VALID_TOOLS`
- `CHANGELOG.md` — modified: behavior-first entry for this task
**Branch:** `git checkout task/050-extract-shared-agent-skills`
**Stage:** `git add REQUIREMENTS_AGENT_SKILLS.md docs/tasks/TASK-050-extract-shared-agent-skills.md docs/tasks/TASK-049-document-manual-venv-activation.md .claude/skills claude-skills .claude/agents claude-agents Makefile scripts/validate_agents.py CHANGELOG.md`
**Commit:** `git commit -m "Extract shared agent procedures into skills (TASK-050)"`
