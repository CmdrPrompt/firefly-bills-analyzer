# TASK-037 Multi-format export support

## Status
todo

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

- [ ] 1. Single CSV format exports all reports to CSV files as before
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Single CSV export works as before"

- [ ] 2. Single JSON format exports all reports to JSON files as before
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Single JSON export works as before"

- [ ] 3. Multiple formats export each report in all listed formats
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Multiple formats export each report in all formats"

- [ ] 4. Invalid config: none combined with other format is rejected at startup
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: none combined with other format is rejected"

- [ ] 5. Invalid config: unsupported format is rejected at startup and named
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: unsupported format is rejected and named"

- [ ] 6. Invalid config: duplicate format is rejected at startup and named
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Invalid config: duplicate format is rejected and named"

- [ ] 7. Each exported file path is printed to terminal
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Each exported file path is printed"

- [ ] 8. CLI --help documents EXPORT_FORMAT as accepting single format or comma-separated list
      See tests/bdd/features/TASK-037-multi-format-export-support.feature: Scenario "Help text documents comma-separated export syntax"

## Out of scope
- Web UI endpoint changes (FR-20 remains scoped; CLI is the primary focus per UC5 alternative flow)
- Export format extensions (only csv and json remain supported; no new formats)
- Changes to export content or field structure (FR-30d, FR-45b, FR-45c, FR-51b, FR-51c unchanged)

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/037-multi-format-export-support`
**Stage:**
**Commit:**
