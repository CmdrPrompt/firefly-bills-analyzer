# TASK-042 Add Task Drafter agent and integrate it into Workflow Guardian

## Status
done

## Description

Split Gherkin-based task-file drafting out of `requirements-drafter` into a
new, dedicated **Task Drafter** agent (`claude-agents/task-drafter.agent.md`
/ `.claude/agents/task-drafter.agent.md`), per confirmed requirements
BDD-036..038 in `REQUIREMENTS_BDD.md` (v1.1.0). BDD-030/031, which previously
assigned this responsibility to requirements-drafter, are marked deprecated
in the same requirements update rather than renumbered.

Task Drafter consumes confirmed REQ-IDs, slices them into INVEST-compliant
task files under `docs/tasks/`, derives Gherkin scenarios mechanically from
each requirement's precondition/trigger/effect, and marks a task `blocked`
whenever a referenced requirement carries an unresolved `[VALUE TBD]` /
`[TRIGGER TBD]`. It never drafts or edits requirement text itself.

`workflow-guardian.agent.md` (both the `templates/` `.tmpl` consumer flavor —
unchanged by this task, see Out of scope — and the `claude-agents/` flavor
used by this repo) is updated to:

- Delegate requirements drafting to Requirements Drafter and task drafting to
  Task Drafter, rather than drafting either itself except as an explicitly
  logged fallback.
- Gate implementation start on the task's Status not being `blocked`.
- Verify Requirements Drafter and Task Drafter output the same way it already
  verifies Implementation Worker and Test Design Reviewer output (Subagent
  verification gate), including a verbatim-diff check that a merged
  requirement matches exactly what the user confirmed.
- Add a `blocked` value to task Status, and a `## Requirements` /
  `## Story` / `## Blockers` section to the task file template, matching
  what Task Drafter now produces.

## Branch

**Branch name:** `task/042-task-drafter-agent`
**Switch/create:** `git checkout -b task/042-task-drafter-agent`
**Make target:** `make branch-task f=TASK-042`

## Requirements

Confirmed in `REQUIREMENTS_BDD.md` v1.1.0: BDD-036, BDD-037, BDD-038 (new),
BDD-032 (amended), BDD-030/BDD-031 (deprecated in place, not renumbered).

## Acceptance criteria

- [x] `REQUIREMENTS_BDD.md` updated with BDD-036..038, amended BDD-032, and
      BDD-030/031 marked deprecated; presented to the user and explicitly
      confirmed ("Is this what you intended?") before finalizing.
- [x] `claude-agents/task-drafter.agent.md` exists with valid YAML
      frontmatter (`tools:` as a list, not a comma-separated string — this
      is the bug that started this task) and passes `make validate-agents`.
- [x] `.claude/agents/task-drafter.agent.md` is an exact copy of
      `claude-agents/task-drafter.agent.md` (dogfooding convention already
      used by every other agent in this repo).
- [x] `claude-agents/workflow-guardian.agent.md` (and its `.claude/agents/`
      copy) reflects the Task Drafter integration: new gates, `blocked`
      status, updated Operating Procedure.
- [x] `CHANGELOG.md` updated with a behavior-first entry.
- [x] `make lint && make test` pass (`ruff check`, `make validate-agents`,
      and `pymarkdown scan` re-run individually on every file this task
      touched — all clean; `make test`: 112 passed, coverage unchanged at
      99%. `make lint`'s aggregate `pymarkdown fix` step still fails on the
      same pre-existing MD025/MD047 issues in unrelated
      `docs/tasks/TASK-039-*.md` / `docs/tasks/TASK-040-*.md` documented in
      TASK-041's Completion notes — not touched by this task).
- [x] `templates/task-drafter.agent.md.tmpl` and the Task Drafter
      integration in `templates/workflow-guardian.agent.md.tmpl` exist so
      `make generate-governance-files` installs Task Drafter and the updated
      guardian correctly into consumer projects' `.github/agents/` (Copilot)
      as well as `.claude/agents/` (the latter already covered by the
      wildcard `cp` in `generate-governance-files`, adjusted scope per user
      follow-up during this task).
- [x] `task-drafter` added to the Makefile's `generate-governance-files`
      agent loop so it is actually rendered for consumer projects.
- [x] `README.md` agent count/table/diagram updated to include
      `task-drafter`.

## Out of scope

- Implementing the rest of `REQUIREMENTS_BDD.md` (pytest-bdd tooling,
  `tests/bdd/`, `make bdd`, the `.feature` file pipeline). That requirements
  document's overall Status remains "Draft, ready for implementation";
  BDD-036..038 are confirmed but the surrounding BDD tooling is still
  unbuilt (BDD-PLANNED, in Task Drafter's own terminology).
- Rewriting historical task files to the new `## Requirements`/`## Story`/
  `## Blockers` template shape.

## Notes

- Origin: the user wrote `task-drafter.agent.md` and the
  `workflow-guardian.agent.md` integration directly, then hit a
  `validate-agents` failure (`'tools' must be a list, got: 'Read, Grep,
  Glob, Write, TodoWrite'`) — a YAML frontmatter typo (comma-separated
  string instead of a list). That fix is included in this task's diff.
- Originally the fix was going to be folded into TASK-041 (already `done`
  at the time), but TASK-041's scope is specifically the cross-workspace
  boundary rule and doesn't cover a new agent; this was split into its own
  task per the user's explicit choice.

## Completion

**Date:** 2026-07-10
**Summary:** Formalized the Task Drafter agent (already written by the user)
via a confirmed requirements amendment (BDD-036..038, amended BDD-032,
deprecated BDD-030/031) in `REQUIREMENTS_BDD.md` v1.1.0. Fixed the
`validate-agents` YAML error (`tools:` as a comma-separated string instead
of a list) in `task-drafter.agent.md`. Followed up on the user's question
about Copilot installability by extending scope to also add
`templates/task-drafter.agent.md.tmpl`, register `task-drafter` in the
Makefile's `generate-governance-files` agent loop, port the Task Drafter
integration into `templates/workflow-guardian.agent.md.tmpl` (adapted to
that template's simpler Copilot-chatmode style — no worktree/subagent-
verification detail, matching its existing level of simplification), and
update `README.md`'s agent count/table/diagram. Full BDD tooling
(pytest-bdd, `.feature` files, `make bdd`) remains unbuilt, per Out of
scope.
**Files changed:**
- `REQUIREMENTS_BDD.md` — modified (BDD-036..038 added, BDD-032 amended, BDD-030/031 deprecated)
- `claude-agents/task-drafter.agent.md` — modified (tools-list fix, trailing newline)
- `.claude/agents/task-drafter.agent.md` — created (synced copy)
- `claude-agents/workflow-guardian.agent.md` — modified (Task Drafter integration, trailing newline)
- `.claude/agents/workflow-guardian.agent.md` — modified (synced copy)
- `templates/task-drafter.agent.md.tmpl` — created
- `templates/workflow-guardian.agent.md.tmpl` — modified (Task Drafter integration)
- `Makefile` — modified (added task-drafter to generate-governance-files agent loop)
- `README.md` — modified (agent count, table, workflow diagram)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-042-task-drafter-agent.md` — created
**Branch:** `git checkout task/042-task-drafter-agent`
**Stage:** `git add REQUIREMENTS_BDD.md claude-agents/task-drafter.agent.md .claude/agents/task-drafter.agent.md claude-agents/workflow-guardian.agent.md .claude/agents/workflow-guardian.agent.md templates/task-drafter.agent.md.tmpl templates/workflow-guardian.agent.md.tmpl Makefile README.md CHANGELOG.md docs/tasks/TASK-042-task-drafter-agent.md`
**Commit:** `git commit -m "Add Task Drafter agent and integrate it into Workflow Guardian, including Copilot scaffolding"`
