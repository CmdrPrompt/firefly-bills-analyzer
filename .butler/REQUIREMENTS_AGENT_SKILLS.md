# Requirements: Shared agent-procedure skills

## Context

Every `.agent.md` file under `.claude/agents/` (mirrored in `claude-agents/`)
previously embedded its own copy of shared procedural knowledge — how to
commit from a worktree, the canonical task-file template, the TDD red/green/
refactor cycle, changelog style, and the characterization-test procedure.
Because each agent restated these rules independently, a change to any one
of them (e.g. a new commit path, a template field) required editing up to
ten files by hand, and drift between agents was easy to introduce and hard
to catch.

## Goals

1. Move procedures shared by two or more agents into a single skill under
   `.claude/skills/` (mirrored in `claude-skills/`), so each procedure has
   exactly one source of truth that agents load with the `Skill` tool
   instead of restating.
2. Keep `.claude/skills/` and `claude-skills/` byte-identical, the same way
   `.claude/agents/` and `claude-agents/` are already kept in sync.
3. Keep every agent's own responsibilities (what it gates, what it verifies,
   its role boundaries) in the agent file itself — only the shared mechanics
   move to skills.

## Non-goals

- Changing what any agent is actually allowed to do (tool grants beyond
  adding `Skill`, role boundaries, gating logic).
- Introducing new procedures — this is an extraction of existing, already
  -agreed rules into a shared location, not new policy.

## Requirement 1: Skills as single source of truth for shared agent procedures

**Description:** For any procedure referenced by two or more agent
definitions (commit workflow, task-file format, TDD cycle, changelog style,
characterization-test procedure), the full procedure text MUST live in
exactly one `.claude/skills/<name>/SKILL.md` file, and every agent that
needs it MUST reference it by name and load it with the `Skill` tool rather
than restating the procedure inline. `.claude/skills/` and `claude-skills/`
MUST be kept byte-identical, enforced by an automated `make lint` check
(mirroring the existing `check-agents-sync` check for `claude-agents/` vs
`.claude/agents/`). Any agent that references a skill MUST have `Skill` in
its `tools:` list, and `Skill` MUST be a value accepted by
`scripts/validate_agents.py`.

**Use case:**

```bash
make lint
# runs check-agents-sync (existing) and check-skills-sync (new): fails the
# build if .claude/skills/<name>/SKILL.md and claude-skills/<name>/SKILL.md
# differ or exist on only one side, mirroring the existing agents-dir check

uv run python scripts/validate_agents.py
# validates every agent's `tools:` list against VALID_TOOLS, which now
# includes "Skill"
```

## Acceptance criteria (overall)

- [ ] `commit-workflow`, `task-file-format`, `tdd-cycle`, `changelog`, and
      `characterization-tests` each exist as a `SKILL.md` under both
      `.claude/skills/` and `claude-skills/`, byte-identical.
- [ ] `make check-skills-sync` (wired into `make lint`) fails if the two
      skill directories drift.
- [ ] Every agent that references a shared procedure has `Skill` in its
      `tools:` list and no longer duplicates that procedure's full text
      inline.
- [ ] `scripts/validate_agents.py` accepts `"Skill"` as a valid tool.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
