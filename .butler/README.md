# python-butler

Shared infrastructure for Python projects — Makefile targets and AI agents for spec-driven, TDD development.

## What's included

- **`Makefile`** — linting, testing, and task workflow targets built on [uv](https://github.com/astral-sh/uv)
- **`claude-agents/`** — Claude Code agent source files
- **`templates/`** — templates for `CLAUDE.md`, Copilot instructions, and Copilot agents
- **`scaffold/`** — project scaffolding templates (`pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`)

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
