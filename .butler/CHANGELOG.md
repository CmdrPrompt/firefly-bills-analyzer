# Changelog

## [Unreleased]

### Added

- `make init-project` interactively prompts for project name, description, requirements
  path, and run command, then delegates to `generate-governance-files`; keeps
  `generate-governance-files` CI-safe while giving humans a guided entry point. (TASK-002)
- README now has separate step-by-step adoption flows for new and existing projects,
  prerequisites section, and explicit ordering (subtree → include → init-project). (TASK-003)
- README adoption guide clarifies that an initial empty commit is required only when
  the repo was created locally with `git init`, not when cloned from GitHub. (TASK-004)

### Changed

- `templates/CLAUDE.md.tmpl` is now a proper project-scoped CLAUDE.md template with all
  supported placeholders (`{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}`, `{{REQUIREMENTS_PATH}}`,
  `{{WORKFLOW_GUARDIAN_NAME}}`, `{{BUG_TRIAGE_NAME}}`, `{{PROJECT_MAKE_TARGET}}`); previously
  contained the python-butler README. (TASK-001)
- `generate-governance-files` now guards against overwriting an existing `CLAUDE.md` or
  `.github/copilot-instructions.md` unless `FORCE=1` is passed. (TASK-001)
