# TASK-043 Regression test protecting non-recursive architecture

## Status

done

## Requirements

**Binding:** Requirement 1 from REQUIREMENTS_TASK_WORKFLOW.md
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer, I want to protect python-butler against regressions to the
non-recursive architecture, so that consumer projects can never again get stuck
in a situation like firefly-python-api, where a stale vendored `.butler/Makefile`
snapshot would cause `make branch-task` and similar task-workflow commands to
recurse infinitely.

## Description

Implement regression tests asserting that `butler_core.git_ops`'s core branch/
stage/commit/pr/merge functions (`branch_for`, `stage_for`, `commit_for`,
`open_pr_for`, `merge_pr_for`) MUST NOT construct a `subprocess` call whose
first argument is `"make"`, and that end-to-end `butler task <cmd>` invocations
complete without spawning a nested `butler` or `make` process. This test suite
formalizes and protects behavior that already exists in this repo's source as
of TASK-023 and must remain invariant going forward.

No production code changes are required; this is pure test coverage.

## Branch

**Branch name:** `task/043-fix-task-command-make-recursion`
**Switch/create:** `git checkout -b task/043-fix-task-command-make-recursion`
**Make target:** `make branch-task f=TASK-043`

## Acceptance criteria (Gherkin)

- [x] Scenario: `butler_core.git_ops` never constructs subprocess calls to make
      Given the module `butler_core.git_ops` with functions `branch_for`, `stage_for`, `commit_for`, `open_pr_for`, `merge_pr_for`
      When those functions' implementations are inspected (via AST parsing or static analysis)
      Then none of them construct a `subprocess` call whose first argument is the string `"make"`

- [x] Scenario: End-to-end `butler task branch` does not spawn a nested process
      Given a fixture project with an initialized git repository
      When `butler task branch <task-name>` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [x] Scenario: End-to-end `butler task stage` does not spawn a nested process
      Given a fixture project with an initialized git repository and uncommitted changes staged/unstaged
      When `butler task stage` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [x] Scenario: End-to-end `butler task commit` does not spawn a nested process
      Given a fixture project with an initialized git repository and staged changes
      When `butler task commit <message>` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [x] Scenario: End-to-end `butler task pr` does not spawn a nested process
      Given a fixture project with an initialized git repository configured as a mock GitHub project
      When `butler task pr` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [x] Scenario: End-to-end `butler task merge` does not spawn a nested process
      Given a fixture project with an initialized git repository and a mock pull request
      When `butler task merge` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [x] Scenario: CHANGELOG.md updated with behavior-first entry
      Given a current CHANGELOG.md
      When this task is completed
      Then CHANGELOG.md contains a new entry describing the regression test coverage added

- [x] Scenario: Tests pass and coverage maintained
      Given the existing test suite with current coverage baseline
      When `make test` and `make lint` are run after implementation
      Then all tests pass and code coverage does not decrease below the baseline

## Out of scope

- Fixing already-vendored `.butler/Makefile` copies in existing consumer repos (e.g. `firefly-python-api`). Those projects pick up the fix by running `butler sync` (Requirement 3) once it ships.
- Changing the implementation of `butler_core.git_ops` functions themselves — they already implement the correct non-recursive architecture. This task only adds test coverage.
- Modifying the root Makefile task targets — the Makefile already correctly calls `butler task <cmd>` exactly once with no callback.

## Blockers

None

## Completion

**Date:** 2026-07-10
**Summary:** Added `tests/test_no_make_recursion.py`, a regression suite protecting the
non-recursive `butler task <cmd>` <-> vendored `Makefile` architecture (Requirement 1 of
REQUIREMENTS_TASK_WORKFLOW.md). No production code was changed — `butler_core.git_ops` already
implemented the correct non-recursive shape as of TASK-023; this task only formalizes it as an
automated regression test. Coverage: a static AST scan asserts none of `branch_for`, `stage_for`,
`commit_for`, `open_pr_for`, `merge_pr_for` construct a `subprocess` call whose first argument is
`"make"` (hardened during Test Design Review to also catch tuple literals, `shell=True` string
commands, and to flag rather than silently pass any call built through an unresolvable variable
indirection); five end-to-end tests drive `butler_cli.__main__.main` for each subcommand with
`subprocess.run` patched to record every invocation, asserting `"make"`/`"butler"` never appear;
five unit-level tests exercise each `git_ops` function directly as a belt-and-suspenders check.
Non-vacuousness was empirically verified during implementation by temporarily reintroducing a
`["make", ...]` call into `branch_for`, confirming 3 tests failed, then reverting. Test Design
Review (Farley Index 6.8/10 pre-fix) flagged two real issues, both fixed before staging: three
unit tests depended on the live, mutable `docs/tasks/TASK-015-*.md` file instead of an isolated
fixture (now use `create_task` in `tmp_path`, matching the rest of the suite), and the AST scan
only matched list literals (now also matches tuples, `shell=True` strings, and flags variable
indirection). Minor known deviation from the task's literal Gherkin wording: the "process-tree
monitoring" phrasing in the end-to-end scenarios is implemented via patching
`butler_core.git_ops.subprocess.run` and asserting on recorded call arguments rather than
spawning `butler` as a real OS subprocess and inspecting its live process tree — this matches the
simpler pattern shown in REQUIREMENTS_TASK_WORKFLOW.md's own Requirement 1 use case and is
deterministic/fast, at the cost of not literally observing an OS process tree; judged acceptable
since the binding requirement text does not mandate real process-tree inspection, only that no
`butler`/`make` nested process results. `make lint` currently fails on pre-existing
`pymarkdown` MD025/MD047 violations in `docs/tasks/TASK-039-conflict-free-butler-pull.md` and
`docs/tasks/TASK-040-Declare-butler-core-as-dev-dependency-in-consumer-projects.md`; confirmed via
`git show main:...` that both violations already exist on `main`, unrelated to this task, and out
of its scope. `make test` passes cleanly: 124/124 (baseline 112/112), total coverage unchanged at
99%, `git_ops.py` remains 100%.

**Files changed:**

- `tests/test_no_make_recursion.py` — created
- `CHANGELOG.md` — modified (behavior-first entry added)

**Branch:** `git checkout task/043-fix-task-command-make-recursion`
**Stage:** `make stage-current-task`
**Commit:** `git commit -m "Add regression tests protecting the non-recursive butler task <-> Makefile architecture (TASK-043)"`
