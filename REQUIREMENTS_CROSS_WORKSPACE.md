# Requirements: Cross-Workspace Boundary and Task-Dependency Guidelines

## Context

While working across `firefly-bills-analyzer` and its sibling dependency
`firefly-python-api` (both scaffolded from python-butler), an agent edited a
requirements document in the sibling repo — from within the consumer
project's workspace — before the user had approved doing so. The user then
had `firefly-bills-analyzer/CLAUDE.md` amended by hand with a
"Cross-Workspace Boundary" section. That repo also maintains a hand-written
`docs/tasks/README.md` task index encoding execution order and cross-repo
dependencies. Neither pattern exists in python-butler's scaffolding today, so
every consumer project that needs them has to invent its own convention.
(TASK-041)

## Goals

1. Make the cross-workspace boundary rule a first-class, reusable part of
   python-butler's generated `CLAUDE.md`.
2. Make the boundary rule a mandatory enforcement gate in the generated
   Workflow Guardian agent definitions.
3. Decide, and record the decision, whether an optional task-dependency-index
   scaffold artifact is added in this task or deferred to a follow-up task.

## Non-goals

- Retroactively rewriting `firefly-bills-analyzer/CLAUDE.md` or
  `firefly-python-api`'s docs.
- Automated/OS-level enforcement (sandboxing, filesystem permissions) of the
  boundary rule — this is documentation/prompt-level guidance only.
- Defining what "workspace" means for every possible consumer project layout
  (monorepo packages, vendored copies, etc.) beyond the general pattern
  below; consumer projects fill in their own specifics when they adopt the
  template.

## Requirement 1: Cross-Workspace Boundary section in `CLAUDE.md.tmpl`

**Description:** `templates/CLAUDE.md.tmpl` gains a "Cross-Workspace
Boundary" section, generalized from the manually-written one in
`firefly-bills-analyzer/CLAUDE.md`, stating:

- A workspace covers only the current repo. Any sibling/dependency repo
  (including a possibly-stale vendored copy inside the current repo, e.g. a
  `lib/` directory) is out of bounds for direct edits.
- Code must never be written in another workspace from the current one,
  under any circumstances.
- Task files and requirements-doc edits in another repo/workspace are only
  allowed after the user's explicit prior approval — ask first, then edit;
  never edit then ask.
- When a task is blocked on work belonging to another repo, the agent must
  report the blocker to the user (naming the exact missing piece and the
  repo it belongs to) and resume only once the user confirms the dependency
  is in place.

The section is placed after "Task Management" (mirroring the source
project's placement, immediately before its equivalent of "Task
Management" content) and uses plain prose — no new template placeholders are
required, since the rule is project-layout-agnostic.

**Use case:** A consumer project has one or more sibling repos it depends on
(vendored copy or separate workspace). While working a task, the agent hits a
missing method/type that belongs in the sibling repo. Instead of editing the
sibling repo directly, the agent stops, reports the blocker to the user by
name, and only edits the sibling repo's task/requirements files after the
user explicitly approves — never write code there at all.

## Requirement 2: Enforcement gate in Workflow Guardian templates

**Description:** Both `templates/workflow-guardian.agent.md.tmpl` (rendered
via `make generate-governance-files` into a consumer project's
`.github/agents/workflow-guardian.agent.md`) and `claude-agents/workflow-guardian.agent.md`
(copied verbatim into a consumer project's `.claude/agents/` and also the
file this repo uses for its own `.claude/agents/workflow-guardian.agent.md`)
gain a new numbered "Cross-workspace boundary gate" among the Mandatory
Rules, worded consistently with Requirement 1:

- Never write code in a workspace other than the current one.
- Task-file/requirements-doc edits in another workspace require the user's
  explicit prior approval — ask first, then edit.
- If a task is blocked on another workspace, stop and report the blocker
  (missing piece + repo) instead of working around it.

**Use case:** Workflow Guardian is enforcing the standard task workflow and
discovers, mid-task, that finishing requires a change in a sibling repo. The
new gate makes it stop and ask before making any edit there, the same way
the requirements-first gate makes it stop and ask before writing code
without confirmed requirements.

## Requirement 3: Task-dependency-index scaffold — decision

**Description:** A `docs/tasks/README.md`-style task index (execution-order
table + `Depends on`/`Condition` columns + dependency graph, as in
`firefly-bills-analyzer/docs/tasks/README.md`) is a materially separate
feature from Requirements 1–2: it needs its own template, its own governance
rules (keep in sync with task files, update in the same commit as status
changes), and update instructions in the Workflow Guardian's Operating
Procedure. To keep this task scoped and reviewable, that work is **split
into a follow-up task** rather than built here. This task only records the
decision in TASK-041's Decision field; the follow-up task is filed
separately once TASK-041 is done.

**Use case:** N/A (documentation decision, no runtime behavior).

## Acceptance criteria (overall)

- [ ] `templates/CLAUDE.md.tmpl` includes the Cross-Workspace Boundary
      section per Requirement 1.
- [ ] `templates/workflow-guardian.agent.md.tmpl` includes the enforcement
      gate per Requirement 2.
- [ ] `claude-agents/workflow-guardian.agent.md` includes the same
      enforcement gate (and, since python-butler dogfoods its own output,
      `.claude/agents/workflow-guardian.agent.md` in this repo is updated to
      match).
- [ ] TASK-041 records the Requirement 3 decision (deferred to follow-up).
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
