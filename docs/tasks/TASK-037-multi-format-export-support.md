# TASK-037 Multi-format export support

## Status
done

## Requirements
**Binding:** FR-53a, FR-53b, FR-53c, FR-53d, FR-08, FR-45a, FR-51a, FR-29, FR-31, UC5
**BDD mode:** BDD-ACTIVE
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a cash-flow analyst, I want to configure `EXPORT_FORMAT` as a comma-separated list of formats (e.g. `csv,json`) so that I can export all analysis reports (recurring payments, income, household spend) to multiple formats simultaneously, avoiding the need to re-run the analysis when downstream tools require different formats.

## Description
Extend `EXPORT_FORMAT` configuration to accept comma-separated format lists. When multiple formats are configured, each of the three exports (patterns, income, household spend) shall be written once per listed format, each to its own file. Validate the configuration on startup to reject contradictory or invalid values: `none` combined with other formats (FR-53c), unsupported formats, and duplicates, all with clear error messages naming the offending value (FR-53d). Update the CLI --help text to document the comma-separated syntax (FR-29). Ensure each exported file path is printed to the terminal (FR-31, UC5 alternative flow).

## Branch
**Branch name:** `task/037-multi-format-export-support`
**Switch/create:** `git checkout -b task/037-multi-format-export-support`
**Make target:** `make branch-task f=TASK-037`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-037-multi-format-export-support.feature

- [x] 1. Single CSV format exports all reports to CSV files as before
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Single CSV export works as before"

- [x] 2. Single JSON format exports all reports to JSON files as before
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Single JSON export works as before"

- [x] 3. Multiple formats export each report in all listed formats
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Multiple formats export each report in all formats"

- [x] 4. Invalid config: none combined with other format is rejected at startup
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: none combined with other format is rejected"

- [x] 5. Invalid config: unsupported format is rejected at startup and named
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: unsupported format is rejected and named"

- [x] 6. Invalid config: duplicate format is rejected at startup and named
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: duplicate format is rejected and named"

- [x] 7. Each exported file path is printed to terminal
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Each exported file path is printed"

- [x] 8. CLI --help documents EXPORT_FORMAT as accepting single format or comma-separated list
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Help text documents comma-separated export syntax"

## Out of scope
- Web UI endpoint changes (FR-20 remains scoped; CLI is the primary focus per UC5 alternative flow)
- Export format extensions (only csv and json remain supported; no new formats)
- Changes to export content or field structure (FR-30d, FR-45b, FR-45c, FR-51b, FR-51c unchanged)

## Blockers
None

## Completion
**Date:** 2026-09-20
**Summary:** `EXPORT_FORMAT` now accepts a comma-separated list of formats
(`csv`, `json`, or `none`), validated at startup in `Config.from_env()`
(`_parse_export_formats`, FR-53a/c/d). When more than one format is
configured, `_run_exports()` in `__main__.py` writes the patterns, income,
and household spend exports once per listed format, printing each file's
path (FR-53b, FR-31). `--help` documents the new syntax (FR-29). All work
was done via Requirements Drafter / Task Drafter / Implementation Worker per
the Workflow Guardian process, though the initial requirements draft and the
first Task Drafter round were run without worktree isolation (before
Workflow Guardian was explicitly invoked on this task) — the user's explicit
"ja" confirmation of the requirements draft and the task-file draft was
obtained before either was written to disk, satisfying the Requirements-first
and Task-drafting gates' fallback provisions. Test Design Reviewer scored the
new/changed tests 7.9/10 (Farley Index); findings were minor/stylistic
(positional `call.args[]` indexing in 3 `test_main.py` tests, one
low-marginal-value Hypothesis test, one over-bundled then-step) and judged
non-blocking per the Test review gate.
**Files changed:** `src/firefly_bills_analyzer/config.py`,
`src/firefly_bills_analyzer/__main__.py`, `.env.example`,
`tests/test_config.py`, `tests/test_main.py`, `tests/test_cli.py`,
`tests/bdd/steps/test_task_037_steps.py` (new), `CHANGELOG.md`,
`docs/REQUIREMENTS_new.md`, `docs/tasks/TASK-037-multi-format-export-support.md`,
`tests/bdd/features/TASK-037-multi-format-export-support.feature` (new)
**Branch:** `git checkout task/037-multi-format-export-support`
**Stage:** `src/firefly_bills_analyzer/config.py src/firefly_bills_analyzer/__main__.py .env.example tests/test_config.py tests/test_main.py tests/test_cli.py tests/bdd/steps/test_task_037_steps.py CHANGELOG.md docs/tasks/TASK-037-multi-format-export-support.md`
**Commit:** `git commit -m "TASK-037 Multi-format export support via comma-separated EXPORT_FORMAT (FR-53a, FR-53b, FR-53c, FR-53d, FR-08, FR-29, FR-31, FR-45a, FR-51a)"`
