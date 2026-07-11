# Requirements: Uninstall / Cleanup

## Context

python-butler is adopted into a project via `git subtree add` + `make
init-project`, which adds `.butler/`, an `include .butler/Makefile` line, and
generated governance files (`CLAUDE.md`, `.github/copilot-instructions.md`,
`.github/agents/*`, `.claude/agents/*`, plus butler-generated sections of
`pyproject.toml`/`.gitignore`/`.pre-commit-config.yaml`). There is currently
no way to reverse this — a project that wants to switch to different
infrastructure (or simply stop using butler) must manually track down and
remove every trace.

## Goals

1. Provide a `make butler-uninstall` target and an equivalent `butler
   uninstall` CLI command that remove butler-related files/lines from an
   adopting project.
2. Let the user choose **per category** what to remove (subtree, Makefile
   include, governance files) instead of an all-or-nothing removal.
3. Never touch `docs/tasks/` — these are the project's own history, not
   butler infrastructure.
4. Guard against accidental data loss: require a clean working tree (`git
   status` with no changes) unless `--force` is passed, and support
   `--dry-run` to list what would be removed without removing anything.

## Non-goals

- Removing or modifying `docs/tasks/*.md` — never, regardless of flags.
- Deleting git history (the subtree commits remain in the log; only the
  working tree's files are cleaned up).
- Interactive per-file selection within a category — granularity is per
  category, not per file.

## Requirement 1: Category-based removal

**Description:** The uninstall function splits butler's footprint into
categories and only removes the categories the user selects:

| Category | What is removed |
|---|---|
| `subtree` | The `.butler/` directory |
| `makefile` | The `include .butler/Makefile` line in the project's `Makefile` |
| `governance` | `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/agents/`, `.claude/agents/`, butler-generated sections in `.pre-commit-config.yaml`/`.gitignore`/`pyproject.toml` |

`docs/tasks/` is never part of any category and is never removed.

**Use case:** A developer wants to switch to a different agent
infrastructure but keep their task files and their own customized
`CLAUDE.md`.

```bash
butler uninstall --categories subtree,makefile
# removes .butler/ and the Makefile include, leaves CLAUDE.md and
# docs/tasks/ untouched
```

## Requirement 2: Dry-run

**Description:** `--dry-run` lists exactly which files/lines would be
removed or changed, without touching the filesystem.

**Use case:**

```bash
make butler-uninstall DRY_RUN=1
# prints: would remove .butler/, would remove line 3 of Makefile, ...
```

## Requirement 3: Safety guard — clean working tree

**Description:** The command refuses to run if `git status --porcelain` is
not empty, unless `--force` is passed. This prevents uncommitted changes
from being overwritten or lost by accident.

**Use case:**

```bash
butler uninstall --categories governance
# Error: working tree has uncommitted changes. Commit/stash first, or pass --force.
```

## Requirement 4: Works without CLI/butler_core (legacy support)

**Description:** `make butler-uninstall` is implemented as plain shell logic
(grep/sed/rm) directly in `.butler/Makefile`, the same way `butler-trim`
already is, and does NOT require `butler_core`/`butler-cli` to be installed.
This is critical because:

- after `make butler-trim`, only `.butler/Makefile` remains in the adopting
  project — no local `butler_core` code exists to call,
- projects that adopted butler before the CLI/MCP server existed (legacy
  installations) may lack `butler_core` entirely, both locally and as a
  dependency.

`butler uninstall` (CLI) remains a separate, optional interface for those
who already have `butler_core`/`butler-cli` installed and prefer it — but
`make butler-uninstall` is the primary, always-working path and must never
depend on the CLI.

**Constraint:** All category logic (`subtree`, `makefile`, `governance`)
must be expressible in plain POSIX shell/`sed`/`grep`/`rm`, portable enough
to work in a `.butler/Makefile` distributed unchanged to any adopting
project, regardless of the Python environment.

**Use case:** A developer has a two-year-old project that adopted butler
long before the CLI existed, has never run `uv tool install`, and now wants
to remove butler entirely.

```bash
make butler-uninstall CATEGORIES=subtree,makefile,governance
# works without butler_core or butler-cli being installed anywhere
```

## Acceptance criteria (overall)

- [ ] `make butler-uninstall CATEGORIES=subtree,makefile,governance` removes
      exactly the selected categories and leaves `docs/tasks/` untouched.
- [ ] `--dry-run`/`DRY_RUN=1` lists planned changes without writing/deleting
      anything.
- [ ] The command refuses to run on a dirty working tree without `--force`,
      with a clear error message.
- [ ] `butler uninstall` (CLI) and `make butler-uninstall` produce identical
      results.
- [ ] `make butler-uninstall` works standalone in a legacy adopting project
      that has only `.butler/Makefile` and no `butler_core`/`butler-cli`
      installed anywhere.
- [ ] Hypothesis-based tests cover parsing/removal of the Makefile include
      line (edge cases: line missing, appears multiple times, different
      formatting).
- [ ] README documents `butler-uninstall` in a new section, analogous to the
      existing "Adopting" sections.
