# Changelog

## [Unreleased]

### Added

- Added a `task-drafter` agent (Claude Code and GitHub Copilot flavors) that turns confirmed
  requirements into INVEST-compliant task files with Gherkin acceptance criteria, splitting this
  responsibility out of `requirements-drafter`. `workflow-guardian` now delegates task-file
  drafting to it and gates implementation on the task's Status not being `blocked`. (TASK-042)

### Fixed

- `make validate-agents` now flags an `.agent.md` file with a missing `tools:` key as an error
  (`missing required key 'tools'`), the same as an empty `tools: []` list -- previously a fully
  absent `tools:` key silently passed validation even though it produces the identical "subagent
  has no tools" runtime failure the validator exists to catch. (TASK-036)
- Fixed invalid `tools:` frontmatter in all nine `.claude/agents/*.agent.md` definitions (and
  their `claude-agents/` sources): the generic names `read, search, edit, write, execute, todo,
  agent` are not Claude Code tool names and were silently dropped, leaving every subagent with an
  empty tool set. Affected subagents (Test Writer, PR Reviewer, Implementation Worker) narrated
  tool calls as plain text instead of executing them and stalled with zero tool uses, the failure
  mode previously documented in TASK-025. Replaced with the real names (`Read`, `Grep`, `Glob`,
  `Edit`, `Write`, `Bash`, `TodoWrite`, `Task`) and updated the prose in the Tool usage sections
  to match. (TASK-035)
- `make merge-pr`/`make merge-current-task` now read the task branch name from the task file's
  `**Branch name:**` line instead of recomputing it from the filename, fixing a mismatch
  (`task/task-<NNN>-<slug>` vs. the real `task/<NNN>-<slug>` convention) that made these targets
  always fail with "No open PR for branch ..." even when a valid, mergeable PR existed. (TASK-033)
- Pinned the `ruff-pre-commit` hook to `v0.15.20`, matching the project's `ruff` dev dependency,
  and re-sorted `mcp/server.py`'s imports accordingly — the two had drifted apart (`v0.11.0` vs.
  latest), so a commit that passed the pre-commit hook could still fail a plain `make lint`.
  (TASK-033)

- Subagent failure markers older than 60 minutes are no longer reported as gate trip
  conditions. Markers in `.claude/state/agent-failures/` are project-global state shared
  across concurrent sessions; a stale marker from one task could confuse another task's
  session. Stale markers are still consumed (deleted) on read, but are excluded from the
  hard-gate escalation message and exit code. If all found markers are stale, the gate
  exits silently with 0 (matching "no markers found" behavior). Markers with missing or
  unparseable `detected_at` timestamps are treated as fresh (fail toward reporting).
  (TASK-037)
- The subagent zero-tool-call hard gate no longer fires on legitimately tool-free work: a
  marker is now only written when zero tool calls coincide with corroborating evidence of
  the real "narrated tool calls" failure (a tool-narration text pattern, or a coordinator
  follow-up event in the transcript), so a long free-text report with zero tool calls (e.g.
  Test Design Reviewer briefed to work entirely from pasted content) no longer trips the
  gate. Agents whose task is genuinely text-in/text-out can also opt out entirely with a new
  `allow-tool-free: true` frontmatter key (`make validate-agents` validates it as boolean);
  `test-design-reviewer.agent.md` now declares it. Failure markers also carry a `session_id`,
  and `agent_result_gate.py` only treats markers from its own session as candidates to
  trigger, leaving other sessions' markers untouched (previously any marker in any session
  could spuriously trip the gate) while still pruning any marker older than 24 hours
  regardless of session. The gate's stderr directive no longer unconditionally claims a
  frontmatter configuration error: when `validate-agents` passes, it now states that the
  configuration is valid and points at the transcript and marker diagnosis for further
  investigation instead. (TASK-038)

### Added

- Generated `CLAUDE.md` and Workflow Guardian agent definitions now include a Cross-Workspace
  Boundary section/gate: code must never be written in a sibling or dependency repo from the
  current workspace, and task-file/requirements-doc edits in another workspace require the
  user's explicit prior approval before editing. (TASK-041)
- Added `make validate-agents` (`scripts/validate_agents.py`, stdlib-only): validates the YAML
  frontmatter of every `.claude/agents/*.agent.md`: required keys present, `tools:` non-empty and
  containing only real Claude Code tool names (with did-you-mean hints for case errors, and
  `mcp__server__tool` names allowed by pattern). Wired into pre-commit and CI so a broken agent
  definition can never reach `main`. (TASK-035)
- Added a runtime hard gate against silent subagent failure, registered in `.claude/settings.json`:
  `.claude/hooks/subagent_toolcheck.py` (SubagentStop) detects any subagent turn that ends with
  zero `tool_use` blocks and writes a failure marker, and `.claude/hooks/agent_result_gate.py`
  (PostToolUse on `Agent|Task`) picks the marker up in the coordinator's session, runs the
  validator, and exits 2 with a directive to treat the failure as a configuration error and stop
  instead of retrying a subagent that has no tools and cannot comply. (TASK-035)
- Added `make butler-uninstall CATEGORIES=subtree,makefile,governance` to remove butler's
  footprint from an adopting project (the `.butler/` subtree, the Makefile `include` line, and/or
  generated governance files) — supports `DRY_RUN=1` to preview changes and requires a clean
  working tree unless `FORCE=1` is passed. `docs/tasks/` is never touched. Implemented in plain
  shell so it works even in legacy projects with no `butler_core`/`butler-cli` installed. An
  equivalent `butler uninstall --categories ... [--dry-run] [--force]` CLI subcommand is available
  as an optional alternative for projects that already have the CLI installed. (TASK-034)
- README now documents the `butler` CLI (`uv tool install .` or a Git URL) and the standalone MCP
  server (`cd mcp && uv sync`) as optional additions to the base Makefile adoption flow, and a
  new test suite (`tests/test_packaging.py`) locks in the packaging isolation this depends on: the
  MCP server's distribution name can't collide with the `mcp` SDK it depends on, its
  `pyproject.toml` can't pull in `butler_core`'s dev dependencies, and `make check-butler` still
  fails with a clear message (not a traceback) when the CLI isn't installed. (TASK-027)
- A standalone MCP server (`mcp/server.py`, its own `mcp/pyproject.toml`) exposes `list_tasks`,
  `get_task`, `create_task`, `check_acceptance_criterion`, `set_task_status`, `branch_task`,
  `stage_task`, `commit_task`, `open_pr_for_task`, and `merge_task_pr` as MCP tools over stdio,
  each a thin one-to-one wrapper over `butler_core.tasks`/`butler_core.git_ops` with no implicit
  batching of git operations, so Claude Code or any MCP-compatible agent can drive the task
  workflow directly instead of shelling out to `make` or the CLI. The MCP SDK dependency stays
  isolated to `mcp/`'s own environment and does not affect the base package. (TASK-025)
- The `butler` CLI (`src/butler_cli/__main__.py`) now exposes `butler task list [--status ...]`,
  `show`, `create --title --description`, `check --criterion N` (1-based), `branch`, `stage`,
  `commit`, `pr`, and `merge` as thin subcommand wrappers over `butler_core.tasks` and
  `butler_core.git_ops`, so a developer in a terminal (including GitHub Codespaces) can drive
  the full task workflow without `make`. (TASK-024)
- `make merge-worktree` now squash-merges (`git merge --squash`) instead of a plain merge, so
  Workflow Guardian creates the single real commit itself after a worktree sub-agent's work is
  brought in; Implementation Worker now commits from an isolated worktree with
  `make commit-output` (its branch does not match `task/<NNN>-...`, so `stage-current-task`/
  `commit-current-task` aren't available there) instead of leaving edits uncommitted, so its
  work reliably survives worktree cleanup. Workflow Guardian now also reads test/production
  file content itself and pastes it inline into the Test Design Reviewer prompt instead of
  having the reviewer read files independently, and independently re-verifies every
  Implementation Worker / Test Design Reviewer report (file contents, test counts, commit
  hashes, coverage) against ground truth before trusting it. (TASK-029)
- `butler_core.git_ops` provides `branch_for`, `stage_for`, `commit_for`, `open_pr_for`, and
  `merge_pr_for`, extracting the git/`gh` workflow logic previously inlined in the `Makefile`'s
  `branch-task`, `stage-task`, `commit-task`, `pr-task`, and `merge-pr` targets into reusable,
  testable Python operations on the `Task` dataclass, matching the Makefile's behavior and
  error messages exactly. (TASK-023)
- `butler_core.tasks` reads, lists, creates, and updates `docs/tasks/TASK-*.md` files as
  structured `Task` data — `read_task`, `list_tasks`, `create_task`, `check_criterion`,
  `set_status` — while staying byte-compatible with the `grep`/`sed` parsing in `Makefile`
  targets like `branch-task`, `stage-task`, and `commit-task`. (TASK-022)
- `make check-agents-sync` fails `make lint` if `claude-agents/` (the distributable agent
  sources) and `.claude/agents/` (the in-repo copy) have drifted apart, catching missing or
  differing `.agent.md` files before merge instead of silently. (TASK-028)
- Workflow Guardian now requires a Test Design Reviewer pass over a task's tests, checked
  against Dave Farley's 8 Properties of Good Tests, before `make stage-current-task`/
  `stage-task` — real findings must be addressed before staging. (TASK-028)

### Changed

- `make branch-task`, `stage-task`, `commit-task`, `pr-task`, and `merge-pr` (and their
  `-current-task` variants) now delegate to the `butler` CLI instead of inlining `grep`/`sed`
  parsing of task files; target names, `f=TASK-XXX` arguments, and observable behavior are
  unchanged. If `butler-cli` is not installed, these targets now fail with a clear install
  instruction instead of a cryptic `grep`/`sed` error. (TASK-026)
- `tests/test_cli.py::TestGitDelegation` now mocks `subprocess.run` at the real git/`gh`
  process boundary instead of the CLI's internal `git_ops` collaborator functions, so the
  five delegation tests (branch/stage/commit/pr/merge) assert on the actual external command
  the full CLI pipeline would run (and the CLI's exit code) instead of only that an internal
  function was called with a given object — regression protection now survives internal
  signature refactors. (TASK-030)
- `tests/test_cli.py` test names each now state a single behaviour claim: names containing
  "and" were either split into two independent tests (creating a task file vs. printing its
  id, since they're observed through different mechanisms and don't imply one another) or
  renamed to a single unifying name where the two facts were one cohesive behaviour (e.g.
  "prints an error and exits 1" -> "fails cleanly"). (TASK-031)
- `tests/test_cli.py` multi-assert tests (`test_prints_structured_task_data`,
  `test_prints_acceptance_criteria_with_check_marks`, `test_prints_completion_info_when_present`,
  `test_creates_task_file_with_correct_metadata`) now carry a failure message on every `assert`
  stating what was expected, so a failure pinpoints the diverging field without reading the
  test body. (TASK-032)

### Fixed

- `templates/` (the Copilot-facing `.tmpl` counterparts rendered into an adopting project's
  `.github/agents/`) was missing `test-design-reviewer.agent.md.tmpl` and
  `test-writer.agent.md.tmpl`, and `generate-governance-files`'s agent loop didn't generate
  them either; both agents are now templated and included in generation, matching
  `.claude/agents/`. (TASK-029)
- `claude-agents/` was missing `test-design-reviewer.agent.md` and `test-writer.agent.md`,
  and its `workflow-guardian.agent.md` was stale relative to `.claude/agents/`; both
  directories are now identical. (TASK-028)

- Python package skeleton (`pyproject.toml`, `src/butler_core/`, `src/butler_cli/`, `mcp/`,
  `tests/`) and dev dependencies (`ruff`, `mypy`, `bandit`, `pytest`, `hypothesis`) so
  subsequent tasks can implement and test real code. (TASK-021)
- `make sync-main` merges `main` into the current task branch — replaces the previous
  instruction to run `git merge main` directly. (TASK-021)
- `make merge-worktree b=<branch>` merges a worktree sub-agent branch back into the
  current branch after the agent finishes. (TASK-021)
- `make commit-output f="..." m="..."` stages and commits arbitrary files with a given
  message, for agents that operate outside a task branch. (TASK-021)
- Agent files (`implementation-worker`, `requirements-drafter`, `characterization-test-writer`,
  `test-writer`, `bug-triage`, `dependency-auditor`, `test-design-reviewer`) updated with
  `write` tool access, worktree execution context, and a rule to use `make` targets for all
  git operations instead of direct `git` commands. (TASK-021)
- New agent files `test-writer.agent.md` and `test-design-reviewer.agent.md` added to
  `.claude/agents/`. (TASK-021)

### Fixed

- `make pr-task` and `make branch-task` no longer print `fatal: a branch named
  '...' already exists` when the task branch already exists; they now check with
  `git show-ref` and choose the correct `checkout` form silently. (TASK-019)

- `butler-trim` now removes all files and directories under `.butler/` except
  `Makefile` dynamically, replacing a hardcoded list that silently left behind
  any file added to python-butler after the list was written (e.g. `LICENSE`).
  (TASK-018)

- `butler-trim` now records the remote HEAD SHA via `git ls-remote` instead of
  extracting from the squash-merge commit message, which did not reliably match
  the branch tip. `butler-check` now correctly reports "up to date" after a pull.
  (TASK-016)

- `scaffold/pyproject.toml.tmpl`: replaced `"pymarkdown"` with `"pymarkdownlnt>=0.9.36"`,
  added `[build-system]` table, and added `[tool.setuptools.packages.find]` for src-layout
  projects. (TASK-014)
- `scaffold/.gitignore.tmpl`: added `complexipy-results*.json` (hyphen variant) alongside
  the existing `complexipy_results_*.json` entry. (TASK-014)
- Agent `.md.tmpl` files: all ordered-list items now use `1.` so generated files pass
  `pymarkdown --fix` without modification. (TASK-014)

### Added

- `make butler-check` compares the butler commit SHA in `.butler-version` against
  the remote HEAD and reports whether the project is up to date or suggests
  `make butler-pull`. (TASK-016)
- `make butler-trim` now writes `.butler-version` to the project root with the full
  butler commit SHA; `make butler-pull` keeps it current automatically. (TASK-016)

- `scaffold/.pymarkdown` and `make generate-pymarkdown` target: new projects now get a
  `.pymarkdown` config with the standard disabled rules (md003, md013, md022, md024, md032,
  md033, md040, md041). Generated automatically by `make generate-pyproject` and
  `make install`. (TASK-014)

- `make butler-trim` strips `.butler/` down to just `Makefile` after `make init-project`
  has applied all templates and scaffold files; adopting projects no longer commit
  sources that have no ongoing function. (TASK-015)
- `make butler-fetch` pulls the latest butler without trimming, restoring `templates/`,
  `scaffold/`, and `claude-agents/` when governance files need to be regenerated. (TASK-015)
- `make butler-pull` pulls the latest butler and immediately trims — for keeping
  `.butler/Makefile` up to date without regenerating anything. (TASK-015)
- Claude Code agent source files moved to `claude-agents/` (previously `.claude/agents/`);
  `generate-governance-files` updated accordingly. (TASK-015)

### Fixed

- README "Adopting in an existing project": replaced macOS-incompatible `sed -i`
  with a portable `printf | cat` pattern. (TASK-013)
- README "What's included": scaffold description now lists all generated files. (TASK-013)
- README "Governance files": lists all files generated by `init-project`. (TASK-013)
- README "Adopting in an existing project": added commit and push steps. (TASK-013)

### Added

- README "Adopting in a new project" now includes the commit and push steps
  after `make install`. (TASK-012)

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
