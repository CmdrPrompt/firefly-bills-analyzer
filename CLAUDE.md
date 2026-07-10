# firefly-bills-analyzer

Analyzes your Firefly III transaction history to automatically identify recurring payments and create subscriptions (bills) via the Firefly III API. Designed for cash flow planning across the full year, including low-frequency bills such as quarterly and annual payments.

## Spec-Driven Development

All changes must be grounded in the requirements specification at `docs/REQUIREMENTS_new.md`.

Before writing any code for a new feature or change:

1. Update `docs/REQUIREMENTS_new.md` with the relevant requirement(s) and use case(s), bump the version, and add a changelog entry in the spec.
2. Present the updated text and ask the user: "Is this what you intended?"
3. Wait for explicit confirmation.
4. Only then follow the TDD cycle.

If a change cannot be expressed as a requirement and use case, do not implement it.

Decisions the spec explicitly defers live in its **Open Items** table. If a task
file references an Open Item, resolve it with the user before implementing —
never assume a deferred decision has been made.

## Task Management

Tasks live in `docs/tasks/TASK-XXX-short-description.md`. See the Workflow Guardian
agent (`.github/agents/workflow-guardian.agent.md`) for the task file format and full
workflow enforcement.

**Implementation order:** numeric task order is NOT execution order. The
authoritative sequence and dependency graph live in `docs/tasks/README.md` —
consult it before starting any task, and never start a task whose dependencies
are not `done`. When adding a new task file, add it to `docs/tasks/README.md`
(table and graph) in the same commit. When a task's status changes, update the
Status column there in the same commit — in particular, completing a task means
updating BOTH the task file (Status + Completion section) AND the Status column
in `docs/tasks/README.md` before committing. A task is not done until the index
says so. Since `make stage-current-task` stages the files listed in the task
file, `docs/tasks/README.md` must appear in every task's **Files changed** list
— add it when creating a task file, or the index update will not be staged.

**Spec consistency:** before implementing a task, verify that its Description and
acceptance criteria still match the current spec version — task files can go
stale when the spec is revised. If they conflict, the spec wins: update the task
file first and confirm with the user.

**Branch policy:** Every task runs on its own `task/<NNN>-short-description` branch.
Never commit implementation work on `main`.

**Branch sync:** After switching to the task branch, check if it is behind `main`.
If it is, run `git merge main` before writing any code.

**Task workflow:**

```bash
make branch-task f=TASK-001        # create/switch to task branch
# implement, then update CHANGELOG.md, the task file Completion section,
# and the Status column in docs/tasks/README.md
make stage-current-task            # auto-fix and stage files listed in task file
git diff --staged                  # optional review
make commit-current-task           # commit using message from task file — never git commit directly
make pr-current-task               # open GitHub PR
make merge-current-task            # squash-merge when ready, pull main
```

Or with explicit task ID: `make stage-task f=TASK-001`, `make commit-task`, `make pr-task`.

## Bug Discovery

Use the **Bug Triage** agent (`.github/agents/bug-triage.agent.md`) to hunt for
bugs without fixing anything. It analyses code against the requirements spec,
produces a prioritised list, and creates task files for approved bugs.

## TDD

**Red → Green → Refactor.** No exceptions.

- Use **Hypothesis** for all parsing and data transformation functions.
- Coverage must not drop below the task-start baseline when a task is completed.

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
- Do not implement a task in numeric order without checking `docs/tasks/README.md` first.
- Do not implement a task that references an unresolved Open Item without confirming the decision with the user.
- Do not mark a task as done without updating the Status column in `docs/tasks/README.md` in the same commit.