# TASK-044 Automated test for Makefile-CLI flag compatibility

## Status

done

## Requirements

**Binding:** Requirement 2 from REQUIREMENTS_TASK_WORKFLOW.md
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer, I want to ensure the root Makefile and the installed CLI stay
in sync regarding command-line flags, so that a future change to the CLI's
task-directory configuration mechanism (or any other flag interface) cannot ship
without a matching update to the vendored Makefile, or explicit documentation of
a deprecation window.

## Description

Implement an automated test that parses the `butler ...` invocations in the root
`Makefile` and cross-checks every flag they pass (currently `--tasks-dir`)
against the CLI's argparse definition in `src/butler_cli/__main__.py`, failing
the build if any flag the Makefile passes is not accepted by the installed CLI.
This test MUST run as part of `make test`. This holds true today, but the
requirement is to keep it enforced automatically going forward, guarding against
silent drift.

No production code changes are required; this is pure test coverage.

## Branch

**Branch name:** `task/044-makefile-cli-flag-drift-test`
**Switch/create:** `git checkout -b task/044-makefile-cli-flag-drift-test`
**Make target:** `make branch-task f=TASK-044`

## Acceptance criteria (Gherkin)

- [x] Scenario: Test parses butler invocations from root Makefile
      Given the root `Makefile` containing one or more `butler` command invocations
      When a dedicated test extracts all `butler ...` lines from the Makefile
      Then the test successfully parses and identifies all invocations and the flags passed to them

- [x] Scenario: Test cross-checks Makefile flags against CLI argparse
      Given the root Makefile with `butler` invocations passing flags (e.g. `--tasks-dir`) and the CLI's `src/butler_cli/__main__.py` with its argparse definition
      When the dedicated test compares the set of flags used in the Makefile against the set of flags the CLI accepts
      Then the test confirms that every flag passed by the Makefile is accepted by the CLI's argparse definition

- [x] Scenario: Test fails if a flag the Makefile passes is no longer accepted by CLI
      Given the root Makefile passing a flag (e.g. `--deprecated-flag`) that the CLI's argparse no longer recognizes
      When the test is run as part of `make test`
      Then the test fails with a clear error message naming the unrecognized flag(s)

- [x] Scenario: Test runs as part of the standard test suite
      Given the standard test suite (`make test`)
      When the command is invoked
      Then the flag-drift detection test is executed and its result affects the overall pass/fail status

- [x] Scenario: Test passes if all Makefile flags are accepted
      Given the root Makefile with `butler` invocations using only flags accepted by the CLI
      When the test is run
      Then the test passes

- [x] Scenario: CHANGELOG.md updated with behavior-first entry
      Given a current CHANGELOG.md
      When this task is completed
      Then CHANGELOG.md contains a new entry describing the flag-drift detection test added

- [x] Scenario: Tests pass and coverage maintained
      Given the existing test suite with current coverage baseline
      When `make test` and `make lint` are run after implementation
      Then all tests pass and code coverage does not decrease below the baseline

## Out of scope

- Fixing actual flag drift between the Makefile and CLI if it is discovered (that would be a separate bug fix, not test coverage).
- Changing the CLI's argparse definition or the Makefile's `butler` invocations — this task only adds a gate to catch drift.
- Detecting drift in vendored `.butler/Makefile` copies in consumer projects — this task focuses on this repo's root Makefile and CLI.

## Blockers

None

## Completion

**Date:** 2026-07-10
**Summary:** Added `tests/test_makefile_cli_flag_drift.py`, which parses every `butler ...`
invocation in the root Makefile, extracts the long flags passed (currently `--tasks-dir`),
recursively introspects the CLI's argparse tree (`_build_parser()` in
`src/butler_cli/__main__.py`, including all `task` subcommand subparsers), and asserts every
flag the Makefile passes is accepted by the CLI. A synthetic-drift test proves the comparison
logic actually fails and names the offending flag when one isn't recognized. No production code
changed.
**Files changed:** `tests/test_makefile_cli_flag_drift.py` (new), `CHANGELOG.md`,
`docs/tasks/TASK-044-makefile-cli-flag-drift-test.md`
**Branch:** `git checkout task/044-makefile-cli-flag-drift-test`
**Stage:** `git add tests/test_makefile_cli_flag_drift.py CHANGELOG.md docs/tasks/TASK-044-makefile-cli-flag-drift-test.md`
**Commit:** `git commit -m "Add regression test guarding against Makefile-CLI flag drift (TASK-044)"`
