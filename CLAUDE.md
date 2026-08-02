# my-project

Describe your project here.

## Spec-Driven Development

All changes must be grounded in a requirements specification at `docs/REQUIREMENTS.md`.

Before writing any code for a new feature or change:

1. Update `docs/REQUIREMENTS.md` with the relevant requirement(s) and use case(s).
2. Present the updated text and ask the user: "Is this what you intended?"
3. Wait for explicit confirmation.
4. Only then follow the TDD cycle.

If a change cannot be expressed as a requirement and use case, do not implement it.

## Task Management

Tasks live in `docs/tasks/TASK-XXX-short-description.md`. See the Workflow Guardian
agent (`.github/agents/workflow-guardian.agent.md`) for the task file format and full
workflow enforcement.

Workflow Guardian's rules apply automatically to any task-branch/
requirements/TDD work in this repository — they are a standing constraint,
not optional guidance to consult only when the agent is explicitly
`@`-mentioned. The underlying operations (branch/stage/commit/pr/merge,
task-file sync) may be performed via the `make` targets below, the
installed `butler` CLI directly, or the `butler-mcp` MCP server —
whichever is available/configured — interchangeably; what is never
allowed is bypassing all three with a raw `git`/`gh` command.

**Branch policy:** Every task runs on its own `task/<NNN>-short-description` branch.
Never commit implementation work on `main`.

**Branch sync:** After switching to the task branch, check if it is behind `main`.
If it is, run `git merge main` before writing any code.

**Task workflow:**

```bash
make branch-task f=TASK-001        # create/switch to task branch
# implement, then update CHANGELOG.md and task file Completion section
make stage-current-task            # auto-fix and stage files listed in task file
git diff --staged                  # optional review
make commit-current-task           # commit using message from task file — never git commit directly
make pr-current-task               # open GitHub PR
make merge-current-task            # squash-merge when ready, pull main
```

Or with explicit task ID: `make stage-task f=TASK-001`, `make commit-task`, `make pr-task`.

## Cross-Workspace Boundary

This workspace covers only the current repository. Any sibling or dependency
repo (including a possibly-stale vendored copy inside this repo, e.g. a
`lib/` directory) is out of bounds for direct edits.

If a task here is blocked on work that belongs in another repo/workspace
(missing method/type, dependency not yet released, etc.):

- **Never write code** in that other workspace from here, under any
  circumstances.
- Task files and requirements-doc updates in another repo/workspace may be
  made there, but only after stopping and getting the user's explicit
  approval first — do not make the edit and then ask; ask, then edit.
- Report the blocker to the user: name the exact missing piece
  (method/type/task) and the repo it belongs to. Resume implementation
  here only once the user confirms the dependency is in place.

## Bug Discovery

Use the **Bug Triage** agent (`.github/agents/bug-triage.agent.md`) to hunt for
bugs without fixing anything. It analyses code against the requirements spec,
produces a prioritised list, and creates task files for approved bugs.

## TDD

**Red → Green → Refactor.** No exceptions.

- Use **Hypothesis** for all parsing and data transformation functions.
- Coverage must not drop below the task-start baseline when a task is completed.

## Behavior-Driven Development (BDD)

- **Directory layout:** feature files live in `tests/bdd/features/`, step
  definitions live in `tests/bdd/steps/`.
- **Naming:** feature files are named
  `tests/bdd/features/TASK-<NNN>-<short-description>.feature`, matching the
  task file naming in `docs/tasks/`.
- **Style:** scenarios are written in English, in declarative style (what
  the user achieves, not UI mechanics), one behavior per scenario.
- **Criterion mapping:** each acceptance criterion in a task file maps to
  at least one scenario, referencing its criterion ID in a comment or tag
  (e.g. `@AC-3`).
- **Outside-in loop:** bind step definitions first so scenarios fail for
  the right reason, then drive implementation with the inner TDD loop. Do
  not consider a task complete until `make bdd` and `make test` both pass.

## Running the Application

```bash
make help
```

## Changelog

Describe shipped behavior, not internal task bookkeeping.

- Behavior-first language: what was added, changed, or fixed.
- TASK-ID as a suffix reference only.
- Do not write an entry that only says a task was completed.
- Group related work into one bullet rather than one bullet per sub-task.

## What NOT to Do

- Do not write code before the requirements spec is confirmed.
- Do not skip writing tests first (TDD).
- Do not commit code that fails `make lint` or `make test`.
- Do not add dependencies without a clear requirement.
- Do not suppress type errors with `# type: ignore` without explanation.
- Do not run `git commit` directly on a task branch — always use `make commit-current-task`.
