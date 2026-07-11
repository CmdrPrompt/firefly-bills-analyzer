# REQUIREMENTS_BDD.md

**Project:** python-butler
**Feature:** Behavior-Driven Development (BDD) workflow support
**Version:** 1.0.0
**Status:** Draft, ready for implementation
**Target:** Implementation via Claude Code

---

## 1. Purpose

Extend python-butler's spec-driven TDD workflow with BDD as an outer loop.
Acceptance criteria shall be expressed as executable Gherkin scenarios,
verified with pytest-bdd, and enforced by the existing agent workflow.

The change is additive. No existing target, agent, or convention shall be
removed or renamed.

## 2. Definitions

| Term | Meaning |
|------|---------|
| Scenario | A Given/When/Then specification in a `.feature` file |
| Feature file | A file in Gherkin syntax under `tests/bdd/features/` |
| Step definition | Python glue code binding Gherkin steps to test logic |
| Outer loop | BDD scenario: red before implementation, green at completion |
| Inner loop | Existing TDD unit test cycle inside the outer loop |

## 3. Scope

### 3.1 In scope

- pytest-bdd tooling in scaffold templates
- New Makefile targets for BDD execution
- Gherkin acceptance criteria in the task template
- Updates to six agents: requirements-drafter, task-drafter, workflow-guardian,
  implementation-worker, pr-reviewer, characterization-test-writer
- BDD conventions in `CLAUDE.md` and Copilot instruction templates
- Generator support so `make init-project` and
  `make generate-governance-files` emit the BDD additions

### 3.2 Out of scope

- behave, radish, or any runner other than pytest-bdd
- Living-documentation report generation (candidate for v1.1)
- Migration of existing projects' historical tasks to Gherkin
- Cucumber-style tag-based test selection beyond what pytest markers provide

## 4. Requirements

Requirement IDs are stable. Do not renumber on revision; deprecate instead.

### 4.1 Tooling

**BDD-001** The scaffold `pyproject.toml` template SHALL include `pytest-bdd`
in the dev dependency group.

**BDD-002** The scaffold SHALL configure pytest so that `tests/bdd/` is
collected by the default `pytest` invocation.

**BDD-003** The scaffold SHALL create the directory skeleton
`tests/bdd/features/` and `tests/bdd/steps/`, each with a `.gitkeep` or an
example file per BDD-016.

### 4.2 Makefile targets

**BDD-010** The butler Makefile SHALL provide a target `bdd` that runs
`uv run pytest tests/bdd/ -v`.

**BDD-011** The existing `test` target SHALL continue to run the full test
suite, including BDD scenarios, without requiring a separate invocation.

**BDD-012** The butler Makefile SHALL provide a target `bdd-missing` that
lists scenarios without bound step definitions and exits non-zero if any
exist (`pytest --collect-only` based check or pytest-bdd's generation
diagnostics).

**BDD-013** WHEN `make help` is run, the system SHALL list `bdd` and
`bdd-missing` with one-line descriptions.

### 4.3 Conventions

**BDD-015** Feature files SHALL be named
`tests/bdd/features/TASK-<NNN>-<short-description>.feature`, matching the
task file naming in `docs/tasks/`.

**BDD-016** The scaffold SHALL include one example feature file and one
example step definition file demonstrating the conventions, marked clearly
as removable examples.

**BDD-017** Step definitions SHALL live in `tests/bdd/steps/` and SHALL be
reused across features where the wording matches. Agents SHALL search
existing steps before creating new ones.

**BDD-018** Scenarios SHALL be written in English, in declarative style
(what the user achieves, not UI mechanics), one behavior per scenario.

**BDD-019** Each acceptance criterion in a task file SHALL map to at least
one scenario. Each scenario SHALL reference its criterion ID in a comment
or tag (e.g. `@AC-3`).

### 4.4 Task template

**BDD-025** The task template SHALL replace the free-text acceptance
criteria section with a structured section: numbered criteria, each
followed by its Gherkin scenario or a reference to the feature file
containing it.

**BDD-026** The task template SHALL include a field `Feature files:` listing
the `.feature` files belonging to the task.

### 4.5 Agent updates

**BDD-030** *(deprecated — superseded by BDD-036, split into a dedicated
task-drafter agent)* requirements-drafter: WHEN drafting a task, the agent
SHALL express every acceptance criterion as a Gherkin scenario and SHALL
write the corresponding feature file(s) as part of the task deliverable.
EARS patterns map as: precondition to Given, trigger to When, system
response to Then.

**BDD-031** *(deprecated — superseded by BDD-036/037, split into a
dedicated task-drafter agent)* requirements-drafter: IF a criterion cannot
be expressed as an automatable scenario, THEN the agent SHALL mark it
`@manual` with a stated verification method, and SHALL flag this to the
user for confirmation.

**BDD-036** task-drafter (new agent, separate from requirements-drafter):
WHEN given a set of confirmed REQ-IDs, the agent SHALL slice the referenced
requirements into INVEST-compliant task files under `docs/tasks/`, deriving
each Gherkin scenario mechanically from the requirement's precondition
(Given), trigger (When), and obligation/measurable values (Then). The
agent SHALL NOT draft or modify requirement text itself; requirements gaps
are reported back to workflow-guardian for a requirements-drafter round.

**BDD-037** task-drafter: IF a referenced requirement carries a
`[VALUE TBD]`/`[TRIGGER TBD]` placeholder, THEN the resulting task file
SHALL be marked Status `blocked` and SHALL list the placeholder as an open
Blocker; the agent SHALL NOT resolve the placeholder itself, and SHALL NOT
mark a task `todo` or `in-progress` while any blocker remains open.

**BDD-032** workflow-guardian: The agent SHALL NOT approve the start of
implementation unless (a) the task's feature files exist (or, in
BDD-PLANNED/BDD-ABSENT mode per task-drafter's scenario handling, the task
file's inline Gherkin scenarios exist), (b) the task's Status is not
`blocked`, and (c) where `make bdd` is available, it shows the task's
scenarios failing or unbound, confirming red state.

**BDD-038** workflow-guardian: The agent SHALL delegate task-file drafting
to task-drafter (never to requirements-drafter, and never itself except as
an explicitly logged fallback) after requirements confirmation and before
spawning implementation-worker.

**BDD-033** implementation-worker: The agent SHALL work outside-in: first
bind step definitions so scenarios fail for the right reason, then drive
implementation with the inner TDD loop, and SHALL NOT consider the task
complete until `make bdd` and `make test` both pass.

**BDD-034** pr-reviewer: The agent SHALL verify that every acceptance
criterion ID in the task file is covered by a passing scenario, and SHALL
reject the PR listing uncovered criteria otherwise.

**BDD-035** characterization-test-writer: WHEN documenting existing
user-facing behavior, the agent SHOULD prefer Gherkin scenarios; internal
implementation behavior remains plain pytest.

### 4.6 Governance templates

**BDD-040** The `CLAUDE.md` template SHALL include a BDD section covering:
directory layout, naming per BDD-015, style per BDD-018, criterion mapping
per BDD-019, and the outside-in loop per BDD-033.

**BDD-041** The Copilot instructions template and Copilot agent files SHALL
receive the same additions as their Claude counterparts, kept semantically
identical.

**BDD-042** `make init-project` and `make generate-governance-files` SHALL
emit all BDD additions with no new required variables. A new optional
variable `ENABLE_BDD` (default `1`) MAY be provided; when `0`, generators
SHALL omit BDD sections and scaffold entries.

### 4.7 Backward compatibility

**BDD-050** Projects that adopted butler before this version SHALL continue
to work unchanged after `make butler-pull`. BDD targets SHALL degrade
gracefully: IF `tests/bdd/` does not exist, THEN `make bdd` SHALL print an
adoption hint and exit zero.

**BDD-051** `make generate-governance-files FORCE=1` SHALL be the documented
path for regenerating agent files with BDD support in existing projects.

## 5. Acceptance criteria (for this change itself)

1. A fresh project bootstrapped per README steps has `pytest-bdd` installed,
   the `tests/bdd/` skeleton, and passing `make bdd` on the example feature.
2. `make bdd` in a pre-existing butler project without `tests/bdd/` exits 0
   with a hint message.
3. requirements-drafter, given a vague feature idea, produces a task file
   with Gherkin criteria and a matching feature file.
4. workflow-guardian blocks implementation when the feature file is missing.
5. pr-reviewer rejects a PR where criterion `AC-2` has no passing scenario.
6. `make help` lists the new targets.
7. Copilot and Claude agent files are semantically equivalent after
   generation.

## 6. Implementation order

1. Scaffold changes (BDD-001..003, BDD-016)
2. Makefile targets (BDD-010..013, BDD-050)
3. Task template (BDD-025..026)
4. Agent updates (BDD-030..035)
5. Governance templates and generators (BDD-040..042, BDD-051)
6. README update: add BDD to the workflow diagram and conventions section

## 7. Open questions

- Should `bdd-missing` run in pre-commit or only in CI? Proposal: CI only,
  to keep commits fast.
- Tag scheme for manual criteria: `@manual` vs `@no-auto`. Proposal:
  `@manual`.

## 8. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-07-08 | Initial draft |
| 1.1.0 | 2026-07-10 | Split task-drafting out of requirements-drafter into a new task-drafter agent (BDD-036..038); deprecated BDD-030/031 (TASK-042) |
