# python-butler

Shared infrastructure for Python projects — Makefile targets and AI agents for spec-driven, TDD development.

## What's included

- **`Makefile`** — linting, testing, and task workflow targets built on [uv](https://github.com/astral-sh/uv)
- **`claude-agents/`** — Claude Code agent source files
- **`templates/`** — templates for `CLAUDE.md`, Copilot instructions, and Copilot agents
- **`scaffold/`** — project scaffolding templates (`pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`)
- **`scripts/validate_agents.py`**: CI/pre-commit validation of agent definition frontmatter
- **`.claude/hooks/`**: runtime guards for Claude Code subagents (zero-tool-call hard gate)

## Prerequisites

- [uv](https://github.com/astral-sh/uv) — install once with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [gh](https://cli.github.com) — needed for PR and merge targets

## Adopting in a new project

Run all commands from **your project's root**.

```bash
# 1. If you created the repo locally with git init (skip if you cloned from GitHub):
git commit --allow-empty -m "Initial commit"

# 2. Add butler as a subtree
git subtree add --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main --squash

# 3. Create a minimal Makefile that includes butler's targets
echo 'include .butler/Makefile' > Makefile

# 4. Generate CLAUDE.md and all governance files (interactive)
#    init-project prints the exact git add and commit commands to run afterwards
make init-project

# 5. Trim .butler/ down to just the Makefile — everything else has been applied
make butler-trim

# 6. Commit everything
git add -A .butler/ Makefile CLAUDE.md pyproject.toml .gitignore .pre-commit-config.yaml .github/ .claude/
git commit -m "Bootstrap project with python-butler"

# 7. Install dependencies and activate pre-commit hooks
make install

# 8. Push
git push -u origin main
```

## Adopting in an existing project

```bash
# 1. Add butler as a subtree
git subtree add --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main --squash

# 2. Add the include at the TOP of your existing Makefile
#    (butler defines default variable values — placing it first lets
#    your own variable assignments override them)
printf 'include .butler/Makefile\n\n' | cat - Makefile > Makefile.tmp && mv Makefile.tmp Makefile

# 3. Generate governance files (interactive)
#    init-project prints the exact git add and commit commands to run afterwards
make init-project

# 4. Trim .butler/ down to just the Makefile — everything else has been applied
make butler-trim

# 5. Commit
git add -A .butler/ CLAUDE.md pyproject.toml .gitignore .pre-commit-config.yaml .github/ .claude/
git commit -m "Add python-butler"

# 6. Install dependencies and activate pre-commit hooks
make install

# 7. Push
git push -u origin main
```

> **Note:** If your Makefile already defines targets with the same names as butler's
> (e.g. `lint`, `test`), place the `include` *after* your own targets to let yours take
> precedence. Review `make help` after adding the include to spot any conflicts.

## Keeping butler up to date

```bash
make butler-check  # check if updates are available
make butler-pull   # pull latest and trim
```

`butler-pull` trims `.butler/` back to just `Makefile` and records the new
butler version in `.butler-version`. Commit the result afterwards:

```bash
git add -A .butler/ .butler-version
git commit -m "chore: update butler"
```

## Removing butler

If you want to switch to different infrastructure, remove butler's footprint
per category — nothing under `docs/tasks/` is ever touched:

```bash
# Preview what would be removed, without changing anything
make butler-uninstall CATEGORIES=subtree,makefile,governance DRY_RUN=1

# Remove only the .butler/ subtree and the Makefile include line,
# keeping CLAUDE.md and the generated agent files as regular project files
make butler-uninstall CATEGORIES=subtree,makefile

# Remove everything butler generated
make butler-uninstall CATEGORIES=subtree,makefile,governance
```

Categories:

| Category | Removes |
|---|---|
| `subtree` | `.butler/` |
| `makefile` | The `include .butler/Makefile` line in `Makefile` |
| `governance` | `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/agents/`, `.claude/agents/` |

The command refuses to run on a dirty working tree — commit or stash first,
or pass `FORCE=1`. It is implemented in plain shell, so it works even in a
legacy project that adopted butler before the CLI existed and has no
`butler_core`/`butler-cli` installed.

If the CLI is installed, an equivalent `butler uninstall --categories
subtree,makefile,governance [--dry-run] [--force]` command is available.

## Regenerating governance files

If you need to update `CLAUDE.md`, agent files, or other generated files from
the latest templates, restore the butler sources first:

```bash
make butler-fetch                # pull latest butler without trimming
make generate-governance-files   # or make init-project, or individual generate-* targets
make butler-trim                 # trim back to Makefile only
git add -A && git commit -m "chore: regenerate governance files"
```

## Contributing changes back

```bash
git subtree push --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main
# No push access? Push to a fork and open a PR against main instead.
```

## CLI (optional)

The Makefile targets call a small CLI, `butler`, that wraps task-file parsing
and git/gh operations. Adopting butler via the Makefile alone (as described
above) works without installing anything — `make branch-task`, `stage-task`,
etc. run the same logic through `.butler/Makefile` regardless.

Installing the CLI directly is an optional convenience for developers who
want to run `butler` commands (or use the MCP server, see below) outside of
`make`:

```bash
# From a checkout of this repo:
uv tool install .

# Or straight from GitHub, without cloning:
uv tool install git+https://github.com/CmdrPrompt/python-butler.git
```

This installs a `butler` command backed by `butler_cli`/`butler_core`. It is
not published to PyPI — `pip install butler-cli` without a path or URL will
not work; install from source or a Git URL as shown above.

## MCP server (optional)

`mcp/` contains a separate, optional MCP server (`butler-mcp`) that exposes
butler's task and git/gh operations as tools over stdio, for use by Claude
Code or any other MCP-compatible agent. It depends on `butler_core` but ships
its own `pyproject.toml` so the MCP SDK dependency doesn't leak into projects
that only use the Makefile or CLI.

```bash
cd mcp
uv sync
```

Point your MCP client at `uv run --directory mcp server.py` (or the
equivalent absolute path) to use it. Like the CLI, this is a purely optional
addition — nothing else in this repo requires the MCP server to be installed.

## Governance files

`make init-project` generates the following files interactively:
`CLAUDE.md`, `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`,
`.github/copilot-instructions.md`, and all agent files.

To regenerate non-interactively (e.g. in CI):

```bash
make generate-governance-files \
  PROJECT_NAME="your-project" \
  PROJECT_DESCRIPTION="Describe your project." \
  REQUIREMENTS_PATH="docs/REQUIREMENTS.md" \
  PROJECT_MAKE_TARGET="make web"
```

Both commands exit with an error if `CLAUDE.md` already exists. Pass `FORCE=1` to overwrite.

## Agents

Ten agents cover the full development workflow, available in both Claude Code and GitHub Copilot.

```
requirements-drafter → task-drafter → workflow-guardian → test-writer → implementation-worker → pr-reviewer → merge
                                              ↑
                            bug-triage ───────┤
                characterization-test-writer ─┘
                            test-design-reviewer  (on demand)
                            dependency-auditor    (periodic / pre-release)
```

| Agent | When | Purpose |
|---|---|---|
| `requirements-drafter` | Before coding | Turns vague ideas into confirmed, testable requirements |
| `task-drafter` | After requirements confirmed | Slices confirmed requirements into INVEST task files with Gherkin acceptance criteria |
| `workflow-guardian` | Gate | Enforces task branches, TDD, and commit discipline |
| `test-writer` | After requirement confirmed | Writes failing (red) tests before any production code exists |
| `implementation-worker` | Coding | Implements approved work, runs lint/test, commits |
| `pr-reviewer` | Before merge | Checks scope, tests, changelog, and acceptance criteria |
| `bug-triage` | On demand | Finds bugs without fixing — produces task files |
| `characterization-test-writer` | Before refactoring | Documents existing behavior with tests |
| `test-design-reviewer` | On demand | Scores test suites against Farley's 8 Properties (Farley Index) |
| `dependency-auditor` | Periodic | Audits for CVEs, outdated packages, license issues |

### Invoking agents

**Claude Code** — type `@agent-name` in chat, or describe your task and Claude suggests one automatically.

**GitHub Copilot (VS Code 1.101+)** — run `make generate-governance-files` first, then use the **dropdown** at the bottom of the Copilot Chat panel to select an agent.

### Agent configuration validation

Claude Code silently drops unknown tool names in an agent's `tools:` frontmatter.
A typo can therefore leave a subagent with **no tools at all**: it then narrates
tool calls as plain text instead of executing them, and the task stalls.
Two layers protect against this:

- **Static validation**: `make validate-agents` checks every
  `.claude/agents/*.agent.md` for valid tool names and required keys, including
  that `tools:` is present and non-empty — an agent file with a missing `tools:`
  key is rejected exactly like one with an empty list, since both leave the
  subagent with no real tools at runtime. It runs in pre-commit and CI, so a
  broken definition never reaches `main`.
- **Runtime hard gate**: two hooks registered in `.claude/settings.json`.
  `subagent_toolcheck.py` (SubagentStop) flags a subagent that finishes a turn
  with zero tool calls **and** corroborating evidence of the real "narrated
  tool calls" failure mode, and `agent_result_gate.py` (PostToolUse on
  `Agent|Task`) escalates the flag to the coordinator, instructing it how to
  proceed depending on whether `make validate-agents` confirms a real
  configuration problem.

  **Corroborating-evidence heuristic (TASK-038):** a subagent turn with zero
  tool calls is not automatically treated as a failure — some agents are
  deliberately briefed to work entirely from pasted content and legitimately
  produce a long free-text report with no tool calls at all. A marker is only
  written when zero tool calls coincide with at least one signature of the
  real failure: (a) an assistant text block matching a tool-narration pattern
  — a bare tool name immediately followed by a JSON object of arguments, or a
  response consisting solely of a JSON object — or (b) a coordinator
  follow-up event in the transcript (`isMeta: true` with
  `origin.kind == "coordinator"`), indicating the coordinator already
  observed a stalled turn. A long free-text final report with zero tool
  calls and neither signature does not trigger the gate.

  **Per-agent opt-out:** agents whose task is genuinely text-in/text-out
  (e.g. `test-design-reviewer`) can declare `allow-tool-free: true` in their
  `.agent.md` frontmatter to skip the check entirely, regardless of
  evidence. `make validate-agents` accepts the key and rejects non-boolean
  values.

  **Session-scoped markers:** `.claude/state/agent-failures/` is
  project-global state, shared across all concurrent sessions. Each marker
  now carries the `session_id` of the session that wrote it; a gate run only
  treats markers from its own session as candidates to trigger, leaving
  markers from other sessions in place for their own session to consume.
  Regardless of session, any marker older than 24 hours is pruned (deleted)
  on every run to prevent unbounded accumulation.

  **Stale marker handling:** same-session markers older than 60 minutes are
  treated as informational only: they are still consumed (deleted) on read,
  but not included in the error message or gate escalation. If all
  same-session markers are stale, the gate exits silently with 0 (same as
  "no markers found") rather than tripping for something no longer
  actionable. Markers with missing or unparseable timestamps are treated as
  fresh (fail toward reporting, not toward silent dropping).

  **Gate message wording:** when `make validate-agents` passes, the gate's
  directive states that the configuration is valid and points the
  coordinator at the subagent transcript and marker diagnosis for further
  investigation, instead of unconditionally claiming a frontmatter error.
  When `validate-agents` fails (or is missing), the message keeps the
  configuration-error framing and tells the coordinator not to retry until
  it passes.

Claude Code silently drops unknown tool names in an agent's `tools:` frontmatter.
A typo can therefore leave a subagent with **no tools at all**: it then narrates
tool calls as plain text instead of executing them, and the task stalls.
Two layers protect against this:

- **Static validation**: `make validate-agents` checks every
  `.claude/agents/*.agent.md` for valid tool names and required keys, including
  that `tools:` is present and non-empty — an agent file with a missing `tools:`
  key is rejected exactly like one with an empty list, since both leave the
  subagent with no real tools at runtime. It runs in pre-commit and CI, so a
  broken definition never reaches `main`.
- **Runtime hard gate**: two hooks registered in `.claude/settings.json`.
  `subagent_toolcheck.py` (SubagentStop) flags any subagent that finishes a turn
  with zero tool calls, and `agent_result_gate.py` (PostToolUse on `Agent|Task`)
  escalates the flag to the coordinator as a blocking configuration error,
  instructing it to stop instead of retrying a subagent that cannot comply.

 `scripts/validate_agents.py`.
Extend it when new tools are adopted.

## Conventions

- Tasks live in `docs/tasks/TASK-<NNN>-short-description.md`
- Every task runs on its own `task/<NNN>-short-description` branch
- Always commit via `make commit-current-task`, never `git commit` directly

## License

[MIT](LICENSE)
