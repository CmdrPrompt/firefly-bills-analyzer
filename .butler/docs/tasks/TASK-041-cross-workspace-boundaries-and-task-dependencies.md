# TASK-041 Cross-workspace boundary and task-dependency guidelines

## Status

done

## Background

While working across `firefly-bills-analyzer` and its sibling dependency
`firefly-python-api` (both scaffolded from python-butler), Claude edited a
requirements document in the sibling repo — from within the consumer
project's workspace — before the user had approved doing so. The user then
asked for `firefly-bills-analyzer/CLAUDE.md` to be amended by hand with a
"Cross-Workspace Boundary" section stating: code must never be developed in
another workspace from the current one, and task files / requirements-doc
edits in another repo are only allowed after the user's explicit prior
approval (ask first, then edit — not edit then ask).

Separately, that same project maintains a `docs/tasks/README.md` task index
that encodes execution order and a dependency graph between tasks (numeric
task IDs are not execution order; each task lists `Depends on` and, where
relevant, a `Condition` noting a dependency living in another repo). This
index was written by hand for that one project; python-butler's scaffolding
has no equivalent template today, so every consumer project that wants
ordered/dependent tasks (or cross-repo dependencies) has to invent this
convention itself.

**No requirements for this task have been written yet.** Unlike most
python-butler tasks, there is no existing `REQUIREMENTS_*.md` entry to point
to — drafting the requirement(s) and use case(s) for this feature, per
python-butler's own spec-driven-development flow, is in scope for this task,
not a prerequisite already done. A new `REQUIREMENTS_*.md` file (or a section
in an existing one — TBD during requirements drafting) must be created and
confirmed with the user before any template/agent changes are implemented.

## Goal

Make the cross-workspace boundary rule and task-dependency/ordering pattern
first-class, reusable parts of python-butler's scaffolding, so new and
existing consumer projects get both without hand-authoring them per-project.

## Approach (tentative — subject to change during requirements drafting)

1. Draft requirements: define what "workspace" means for python-butler's
   purposes, what triggers the boundary rule (sibling repos, monorepo
   packages, vendored/stale `lib/` copies, etc.), and what the task-dependency
   index should guarantee (ordering, `Depends on`, cross-repo `Condition`
   notes). Present to the user and get explicit confirmation before coding.
2. Add a "Cross-Workspace Boundary" section to `templates/CLAUDE.md.tmpl`
   (mirroring the one manually added to `firefly-bills-analyzer/CLAUDE.md`),
   parameterized where needed (e.g. `{{WORKFLOW_GUARDIAN_NAME}}` style
   placeholders already used elsewhere in the template).
3. Extend `templates/workflow-guardian.agent.md.tmpl` with an enforcement gate
   for the boundary rule (never write code in another workspace; task/spec
   edits elsewhere require prior explicit user approval) and, if requirements
   confirm it, a gate for consulting a task-dependency index before starting
   work.
4. Evaluate whether a `docs/tasks/README.md`-style task index template
   (execution order table + dependency graph, as seen in
   `firefly-bills-analyzer/docs/tasks/README.md`) should be added as an
   optional scaffold artifact, and if so add it under `scaffold/` /
   `templates/` with its own governance rules (keep in sync with task files,
   update in the same commit as status changes, etc.).
5. Update README/docs describing scaffolded output to mention the new
   section(s).

## Requirements

Drafted and confirmed by the user in `REQUIREMENTS_CROSS_WORKSPACE.md`
(Requirements 1–3).

## Decision: task-dependency-index scaffold (Requirement 3)

**Deferred to a follow-up task.** The `docs/tasks/README.md`-style execution
order/dependency-graph index is a materially separate feature from the
cross-workspace boundary gate (own template, own governance rules, own
Workflow Guardian Operating Procedure update). Building it here would expand
this task's scope beyond what's reviewable in one change. This task only
ships Requirements 1–2 (boundary rule in `CLAUDE.md.tmpl` and the Workflow
Guardian templates); the task-dependency index is filed as a separate
follow-up task once TASK-041 is done.

## Branch

**Branch name:** `task/041-cross-workspace-boundaries-and-task-dependencies`
**Switch/create:** `git checkout -b task/041-cross-workspace-boundaries-and-task-dependencies`
**Make target:** `make branch-task f=TASK-041`

## Acceptance criteria

- [x] Requirements drafted in a new or existing `REQUIREMENTS_*.md`, presented
      to the user, and explicitly confirmed ("Is this what you intended?")
      before implementation begins.
- [x] `templates/CLAUDE.md.tmpl` includes a cross-workspace boundary section
      consistent with the confirmed requirements.
- [x] `templates/workflow-guardian.agent.md.tmpl` enforces the boundary rule
      as a mandatory gate.
- [x] `claude-agents/workflow-guardian.agent.md` (and this repo's
      `.claude/agents/workflow-guardian.agent.md` copy) enforces the same
      gate.
- [x] Decision recorded (in the task file) on whether a task-dependency-index
      template is added in this task or split into a follow-up task.
- [x] `CHANGELOG.md` updated with a behavior-first entry.
- [x] `make lint && make test` pass (`make test`: 112 passed, coverage
      unchanged at 99%, no regression from the 355-stmt/4-miss baseline;
      `make lint` fails only on pre-existing MD025/MD047 issues in
      `docs/tasks/TASK-039-*.md` and `docs/tasks/TASK-040-*.md`, confirmed
      present on `main` before this task via `git stash` and unrelated to
      the four files this task changed).

## Completion

**Date:** 2026-07-10
**Summary:** Drafted and confirmed requirements in `REQUIREMENTS_CROSS_WORKSPACE.md`
(Requirements 1–3). Added a "Cross-Workspace Boundary" section to
`templates/CLAUDE.md.tmpl` and a matching "Cross-workspace boundary gate" to
both Workflow Guardian template flavors (`templates/workflow-guardian.agent.md.tmpl`
and `claude-agents/workflow-guardian.agent.md`, the latter resynced into this
repo's own `.claude/agents/workflow-guardian.agent.md`). Requirement 3's
task-dependency-index scaffold was deferred to a follow-up task per the
Decision section above, not built here. Implementation was delegated to
Implementation Worker in an isolated worktree and independently verified
(diff review, commit hash, `make lint`/`make test` re-run) before merging.
**Files changed:**

- `REQUIREMENTS_CROSS_WORKSPACE.md` — created
- `templates/CLAUDE.md.tmpl` — modified
- `templates/workflow-guardian.agent.md.tmpl` — modified
- `claude-agents/workflow-guardian.agent.md` — modified
- `.claude/agents/workflow-guardian.agent.md` — modified (resynced copy)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-041-cross-workspace-boundaries-and-task-dependencies.md` — modified

**Branch:** `git checkout task/041-cross-workspace-boundaries-and-task-dependencies`
**Stage:** `git add REQUIREMENTS_CROSS_WORKSPACE.md templates/CLAUDE.md.tmpl templates/workflow-guardian.agent.md.tmpl claude-agents/workflow-guardian.agent.md .claude/agents/workflow-guardian.agent.md CHANGELOG.md docs/tasks/TASK-041-cross-workspace-boundaries-and-task-dependencies.md`
**Commit:** `git commit -m "Mark TASK-041 done"`

## Out of scope

- Retroactively rewriting `firefly-bills-analyzer/CLAUDE.md` or
  `firefly-python-api`'s docs — those already have the manually-added
  section; this task only affects python-butler's scaffolding for future/
  other consumer projects.
- Automated tooling that enforces the boundary rule at the OS/filesystem
  level (e.g. sandboxing) — this task is documentation/prompt-level guidance
  for the agents only.

## Notes

- Source context: the manually-added section in
  `firefly-bills-analyzer/CLAUDE.md` (see that repo's git history around
  2026-07-10) is a useful starting draft for the boundary language, but was
  written ad hoc for one project and should be generalized during
  requirements drafting, not copied verbatim.
- Update CHANGELOG.md.
