# Changelog

## [Unreleased]

### Added

- `make init-project` now generates `.gitignore` from `scaffold/.gitignore.tmpl`;
  `make install` also auto-generates it if missing. (TASK-010)
- `make init-project` now generates `.pre-commit-config.yaml` from scaffold with
  ruff hooks; `make install` also auto-generates it if missing, eliminating the
  "No .pre-commit-config.yaml file was found" warning on first commit. (TASK-011)

### Changed

- Scaffold `pyproject.toml.tmpl` now sets ruff `line-length = 100` instead of 88. (TASK-008)
- `make init-project` now prints the suggested `git add` and `git commit` commands
  after successful generation so the user can copy-paste them. (TASK-009)

### Added

- `make init-project` interactively prompts for project name, description, requirements
  path, and run command, then delegates to `generate-governance-files`; keeps
  `generate-governance-files` CI-safe while giving humans a guided entry point. (TASK-002)
- `make init-project` now defaults the project name prompt to the current directory
  name instead of the static `my-project` placeholder. (TASK-007)
- README now has separate step-by-step adoption flows for new and existing projects,
  prerequisites section, and explicit ordering (subtree → include → init-project). (TASK-003)
- README adoption guide clarifies that an initial empty commit is required only when
  the repo was created locally with `git init`, not when cloned from GitHub. (TASK-004)

### Fixed

- `make init-project` now generates `pyproject.toml` with the collected project name
  and description; previously `make install` would generate it with default values
  (`my-project`, `Describe your project here.`). (TASK-005)
- `generate-pyproject` now guards against overwriting an existing `pyproject.toml`
  unless `FORCE=1` is passed. (TASK-005)

### Changed

- `TESTS_DIR ?= tests` added to Makefile alongside `SRC_DIR`; `test` target now passes
  `$(TESTS_DIR)/` explicitly to pytest; `scaffold/pyproject.toml.tmpl` uses `{{TESTS_DIR}}`
  placeholder for `testpaths` instead of hardcoded `tests`. (TASK-006)

- `templates/CLAUDE.md.tmpl` is now a proper project-scoped CLAUDE.md template with all
  supported placeholders (`{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}`, `{{REQUIREMENTS_PATH}}`,
  `{{WORKFLOW_GUARDIAN_NAME}}`, `{{BUG_TRIAGE_NAME}}`, `{{PROJECT_MAKE_TARGET}}`); previously
  contained the python-butler README. (TASK-001)
- `generate-governance-files` now guards against overwriting an existing `CLAUDE.md` or
  `.github/copilot-instructions.md` unless `FORCE=1` is passed. (TASK-001)
