---
name: task-file-format
description: "Use when creating, validating, or updating a task file in docs/tasks/. Defines the canonical TASK-XXX file template, naming convention, status rules, blocker handling, and which roles may edit which sections. Keywords: task file, TASK-XXX, docs/tasks, acceptance criteria, Gherkin, blocker, Completion."
---

# Task file format

Every task lives in `docs/tasks/<TASK-ID>-short-description.md`, where the
TASK-ID is `TASK-<NNN>` with NNN zero-padded to 3 digits. Assign the next ID
by scanning `docs/tasks/` for the highest existing one. The matching branch
is `task/<NNN>-short-description`.

## Canonical template

Use this template exactly:

```markdown
# <TASK-ID> Short description

## Status
todo | in-progress | blocked | done

## Requirements
**Binding:** REQ-XXX, REQ-YYY
**BDD mode:** BDD-ACTIVE | BDD-PLANNED | BDD-ABSENT
**Depends on:** TASK-MMM or "none"
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a <role>, I want <capability>, so that <benefit>.

## Description
What needs to be done and why.

## Branch
**Branch name:** `task/<NNN>-short-description`
**Switch/create:** `git checkout -b task/<NNN>-short-description`
**Make target:** `make branch-task f=<TASK-ID>`

## Acceptance criteria (Gherkin)
- [ ] Scenario: <name derived from the requirement's trigger and effect>
      Given <precondition / state from the requirement's WHILE/IF clause>
      When <trigger from the requirement's WHEN clause>
      Then <observable effect with the requirement's measurable values>
- [ ] Scenario: <error/boundary case>
      ...

## Out of scope
- <explicit exclusions, including negative/scope-exclusion requirements>

## Blockers
- [ ] REQ-XXX carries [VALUE TBD] for <parameter>: must be resolved before implementation
- (write "None" if empty)

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/<NNN>-short-description`
**Stage:** `git add path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Short imperative summary of what was done"`
```

## Rules

- Every task references at least one REQ-ID, and every referenced REQ-ID must
  exist verbatim in the requirements document.
- The Precedence section (requirements binding, story is context) must be
  present verbatim in every task file.
- Every measurable value from the referenced requirements (time, threshold,
  capacity) appears verbatim in a Then step.
- A `[VALUE TBD]` or `[TRIGGER TBD]` in a referenced requirement appears as
  `<TBD: parameter>` in the scenario AND as an open item under Blockers.
- A task with any open Blocker has Status `blocked` and must not be
  implemented. Only the user can waive a blocker.
- The `**Commit:**` line is the message used by `make commit-current-task` -
  keep it a single short imperative sentence.
- `CHANGELOG.md` must always be in the Stage list.

## Status transitions and role boundaries

- Drafting roles (Task Drafter, Bug Triage, Dependency Auditor, Test Design
  Reviewer) fill in every section except Completion, and set Status only to
  `todo` or `blocked`.
- The Workflow Guardian owns the `in-progress` and `done` transitions and is
  the only role that edits Status and Completion on an existing task. It
  never hand-edits stories, scenarios, or blockers.
- Acceptance criteria checkboxes are checked off only by the Workflow
  Guardian, one by one, after it has verified with its own tool calls that
  the corresponding automated test exists and passes.
