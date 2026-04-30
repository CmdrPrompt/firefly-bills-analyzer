# TASK-015 Add butler-trim, butler-fetch, and butler-pull targets

## Status
done

## Description

When a project adopts python-butler via `git subtree add --prefix=.butler`, the
entire butler repo lands in `.butler/`. Most of it has no function in an adopting
project once governance files have been generated. Committing it is unnecessary
noise in the adopting repo's history.

This task adds three Makefile targets:

- **`butler-trim`** — removes everything from `.butler/` except `Makefile`, which
  is the only file needed for daily use. Run after `make init-project`.
- **`butler-fetch`** — pulls the latest butler via git subtree without trimming,
  restoring `templates/`, `scaffold/`, and `claude-agents/` so governance files
  can be regenerated.
- **`butler-pull`** — pulls the latest butler and immediately trims, for when you
  only want to update `.butler/Makefile` without regenerating anything.

Files removed by `butler-trim`:
- `.butler/.claude/` — butler's dev-agent definitions and local settings
- `.butler/.gitignore` — butler's own gitignore
- `.butler/CHANGELOG.md` — butler's release notes
- `.butler/claude-agents/` — agent sources (already copied to `.claude/agents/` by `init-project`)
- `.butler/docs/` — butler's tasks and internal documentation
- `.butler/README.md` — butler's README
- `.butler/scaffold/` — scaffolding templates (already applied by `init-project`)
- `.butler/templates/` — governance templates (already applied by `init-project`)

Only `.butler/Makefile` remains after trim.

Regeneration workflow (when governance files need updating):
```bash
make butler-fetch                  # restore templates/scaffold/claude-agents/
make generate-governance-files     # or make init-project, or individual generate-* targets
make butler-trim                   # clean up again
git add ... && git commit ...
```

## Branch
**Branch name:** `task/015-butler-trim-target`
**Switch/create:** `git checkout -b task/015-butler-trim-target`
**Make target:** `make branch-task f=TASK-015`

## Acceptance criteria

- [x] `make butler-trim` removes `.butler/.claude/`, `.butler/.gitignore`,
  `.butler/CHANGELOG.md`, `.butler/claude-agents/`, `.butler/docs/`,
  `.butler/README.md`, `.butler/scaffold/`, `.butler/templates/` via
  `git rm -r --ignore-unmatch` (idempotent: safe to run twice)
- [x] Only `.butler/Makefile` remains after `butler-trim`
- [x] `make butler-fetch` runs `git subtree pull --prefix=.butler $(BUTLER_REMOTE) main --squash`
  without trimming, restoring all source files
- [x] `make butler-pull` runs `git subtree pull` then `butler-trim`
  (updates `.butler/Makefile` only)
- [x] `BUTLER_REMOTE` defaults to `https://github.com/CmdrPrompt/python-butler.git`
  and can be overridden by the caller
- [x] README adoption guide shows `butler-trim` after `init-project`, not before
- [x] README documents the `butler-fetch` → regenerate → `butler-trim` workflow
- [x] `make lint && make test` pass in the butler repo

## Completion
**Date:** 2026-04-30
**Summary:** Added `butler-trim`, `butler-fetch`, and `butler-pull` targets. `butler-trim` removes everything from `.butler/` except `Makefile`. `butler-fetch` restores sources without trimming for regeneration. `butler-pull` fetches + trims. Moved Claude Code agent sources to `claude-agents/`. Updated README adoption flows and added regeneration workflow section.
**Files changed:** `Makefile`, `claude-agents/` (new, 7 files), `README.md`, `CHANGELOG.md`, `docs/tasks/TASK-015-butler-trim-target.md`
**Branch:** `task/015-butler-trim-target`
**Stage:** `git add Makefile claude-agents/ README.md CHANGELOG.md docs/tasks/TASK-015-butler-trim-target.md`
**Commit:** `git commit -m "Add butler-trim, butler-fetch, butler-pull; trim .butler/ to Makefile only (TASK-015)"`
