# python-butler

Shared infrastructure for Python projects — Makefile targets and AI agents for spec-driven, TDD development.

## What's included

- **`Makefile`** — linting, testing, and task workflow targets built on [uv](https://github.com/astral-sh/uv)
- **`.claude/agents/`** — Claude Code agents
- **`templates/`** — templates for `CLAUDE.md`, Copilot instructions, and Copilot agents
- **`scaffold/`** — project scaffolding templates (e.g. `pyproject.toml`)

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
make init-project

# 5. Install dependencies and activate pre-commit hooks
make install
```

## Adopting in an existing project

```bash
# 1. Add butler as a subtree
git subtree add --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main --squash

# 2. Add the include at the TOP of your existing Makefile
#    (butler defines default variable values — placing it first lets
#    your own variable assignments override them)
sed -i '1s/^/include .butler\/Makefile\n\n/' Makefile

# 3. Generate governance files
make init-project

# 4. Install dependencies and activate pre-commit hooks
make install
```

> **Note:** If your Makefile already defines targets with the same names as butler's
> (e.g. `lint`, `test`), place the `include` *after* your own targets to let yours take
> precedence. Review `make help` after adding the include to spot any conflicts.

## Keeping butler up to date

```bash
git subtree pull --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main --squash
```

## Contributing changes back

```bash
git subtree push --prefix=.butler \
  https://github.com/CmdrPrompt/python-butler.git main
# No push access? Push to a fork and open a PR against main instead.
```

## Governance files

`make init-project` generates `CLAUDE.md`, `.github/copilot-instructions.md`, and all
agent files interactively. To regenerate non-interactively (e.g. in CI):

```bash
make generate-governance-files \
  PROJECT_NAME="your-project" \
  PROJECT_DESCRIPTION="Describe your project." \
  REQUIREMENTS_PATH="docs/REQUIREMENTS.md" \
  PROJECT_MAKE_TARGET="make web"
```

Both commands exit with an error if `CLAUDE.md` already exists. Pass `FORCE=1` to overwrite.

## Agents

Seven agents cover the full development workflow, available in both Claude Code and GitHub Copilot.

```
requirements-drafter → workflow-guardian → implementation-worker → pr-reviewer → merge
                               ↑
             bug-triage ───────┤
 characterization-test-writer ─┘
             dependency-auditor  (periodic / pre-release)
```

| Agent | When | Purpose |
|---|---|---|
| `requirements-drafter` | Before coding | Turns vague ideas into confirmed, testable requirements |
| `workflow-guardian` | Gate | Enforces task branches, TDD, and commit discipline |
| `implementation-worker` | Coding | Implements approved work, runs lint/test, commits |
| `pr-reviewer` | Before merge | Checks scope, tests, changelog, and acceptance criteria |
| `bug-triage` | On demand | Finds bugs without fixing — produces task files |
| `characterization-test-writer` | Before refactoring | Documents existing behavior with tests |
| `dependency-auditor` | Periodic | Audits for CVEs, outdated packages, license issues |

### Invoking agents

**Claude Code** — type `@agent-name` in chat, or describe your task and Claude suggests one automatically.

**GitHub Copilot (VS Code 1.101+)** — run `make generate-governance-files` first, then use the **dropdown** at the bottom of the Copilot Chat panel to select an agent.

## Conventions

- Tasks live in `docs/tasks/TASK-<NNN>-short-description.md`
- Every task runs on its own `task/<NNN>-short-description` branch
- Always commit via `make commit-current-task`, never `git commit` directly
