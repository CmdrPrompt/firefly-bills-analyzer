# TASK-016 Add butler version tracking and butler-check target

## Status
done

## Description

After `butler-trim`, only `.butler/Makefile` remains — there is no way to know
which version of butler a project is pinned to or whether updates are available.

This task adds lightweight version tracking:

- **`butler-trim`** writes a `.butler-version` file to the project root containing
  the butler commit SHA extracted from the git subtree squash-merge message.
  The file is committed alongside `.butler/Makefile` as part of the adoption flow.
- **`make butler-check`** reads `.butler-version`, fetches the remote HEAD SHA via
  `git ls-remote`, and reports whether the project is up to date or updates are
  available.
- **`butler-pull`** already calls `butler-trim`, so `.butler-version` is updated
  automatically on every pull.

No manual version numbers or tags are required — the butler commit SHA is the
version marker.

## Branch
**Branch name:** `task/016-butler-version-check`
**Switch/create:** `git checkout -b task/016-butler-version-check`
**Make target:** `make branch-task f=TASK-016`

## Acceptance criteria

- [x] `make butler-trim` writes `.butler-version` to the project root containing
  the current remote HEAD SHA (fetched via `git ls-remote`)
- [x] `.butler-version` is placed in the project root, not inside `.butler/`
- [x] `make butler-check` reads `.butler-version` and compares it to the remote
  HEAD SHA via `git ls-remote $(BUTLER_REMOTE) refs/heads/main`
- [x] `make butler-check` prints "up to date" when SHAs match, or prints both
  SHAs and suggests `make butler-pull` when they differ
- [x] `make butler-check` assumes updates are available if `.butler-version` does not exist
- [x] `make butler-pull` automatically updates `.butler-version` (via butler-trim)
- [x] `make butler-check` and `make butler-trim` are listed in `make help`
- [x] README "Keeping butler up to date" section documents `make butler-check`

## Completion
**Date:** 2026-04-30
**Summary:** Added `butler-check` target and version tracking via `.butler-version`. `butler-trim` extracts the full butler commit SHA from the subtree squash-merge log entry and writes it to `.butler-version` in the project root. `butler-check` fetches remote HEAD via `git ls-remote` and compares. `butler-pull` stays up to date automatically.
**Files changed:** `Makefile`, `README.md`, `CHANGELOG.md`, `docs/tasks/TASK-016-butler-version-check.md`
**Branch:** `task/016-butler-version-check`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-016-butler-version-check.md`
**Commit:** `git commit -m "Fix butler-trim to record remote HEAD SHA via git ls-remote (TASK-016)"`
