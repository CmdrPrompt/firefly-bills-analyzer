# TASK-034 butler uninstall

## Status

done

## Description

Implement a category-based uninstall/cleanup feature so a project that
adopted python-butler can remove it (fully or partially) when switching to
different infrastructure.

Covers all requirements in REQUIREMENTS_UNINSTALL.md:

- A `make butler-uninstall` Makefile target implemented in plain shell
  (grep/sed/rm) directly in `.butler/Makefile` — must work standalone in a
  legacy adopting project with no `butler_core`/`butler-cli` installed
  anywhere (Requirement 4).
- Category-based removal (`subtree`, `makefile`, `governance`), never
  touching `docs/tasks/`.
- `--dry-run` support that only lists planned changes.
- A clean-working-tree guard (`git status --porcelain` must be empty unless
  `--force` is passed).
- A `butler uninstall` CLI subcommand in `butler_core`/`butler_cli`, as a
  separate optional interface producing identical results to the Makefile
  target — but never a dependency of it.
- README documentation for the new command.

## Branch

**Branch name:** `task/034-butler-uninstall`
**Switch/create:** `git checkout -b task/034-butler-uninstall`
**Make target:** `make branch-task f=TASK-034`

## Acceptance criteria

- [x] `make butler-uninstall CATEGORIES=subtree,makefile,governance` removes exactly the selected categories and leaves `docs/tasks/` untouched
- [x] `--dry-run`/`DRY_RUN=1` lists planned changes without writing/deleting anything
- [x] Command refuses to run on a dirty working tree without `--force`, with a clear error message
- [x] `butler uninstall` (CLI) and `make butler-uninstall` produce identical results
- [x] `make butler-uninstall` works standalone in a legacy project with only `.butler/Makefile` and no `butler_core`/`butler-cli` installed
- [x] Hypothesis-based tests cover parsing/removal of the Makefile include line (missing, duplicated, differently formatted)
- [x] README documents `butler-uninstall` in a new section analogous to "Adopting"
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-09
**Summary:** Added `butler_core/uninstall.py` with `remove_makefile_include` (pure string transform,
Hypothesis-tested for missing/duplicated/whitespace-varied include lines), `plan_uninstall`
(dry-run, touches nothing), and `apply_uninstall` (performs the removal, guarded by an injectable
`dirty_check` so tests stay hermetic; raises `DirtyWorkingTreeError`/`InvalidCategoryError`).
Categories are `subtree`, `makefile`, `governance`; `docs/tasks/` is never a category and a
dedicated test asserts it survives even a full `apply_uninstall` across all three categories.
Wired a `butler uninstall --categories a,b,c [--dry-run] [--force] [--project-root DIR]`
subcommand into `butler_cli/__main__.py` as the optional CLI interface. Per Requirement 4, the
primary interface is `make butler-uninstall CATEGORIES=... [DRY_RUN=1] [FORCE=1]`, implemented as
plain POSIX shell directly in the root `Makefile` (grep/tr/rm, no Python dependency), so it keeps
working in legacy adopting projects that trimmed `.butler/` down to just `Makefile` and never
installed `butler_core`/`butler-cli` — verified manually end-to-end in a throwaway git repo
(dry-run, real removal, dirty-tree refusal, and `FORCE=1` override all behaved as specified, and
`docs/tasks/` was left untouched). The first Test Writer subagent attempt (via
`isolation: "worktree"`) narrated tool calls as plain text instead of invoking them and produced
zero real tool uses across two turns — the same tooling failure documented in TASK-025 — so per
the established fallback rule the tests and implementation were written directly in the main
conversation instead. TDD followed red (ModuleNotFoundError for `butler_core.uninstall`) then
green. Coverage: 99% (65 tests, up from the 34-test/99% baseline at task start — no drop).
**Files changed:**

- `src/butler_core/uninstall.py` — created
- `tests/test_uninstall.py` — created
- `src/butler_cli/__main__.py` — modified (added `uninstall` subcommand)
- `tests/test_cli.py` — modified (added `TestUninstall`)
- `Makefile` — modified (added `butler-uninstall` target)
- `README.md` — modified (added "Removing butler" section)
- `CHANGELOG.md` — modified
- `REQUIREMENTS_UNINSTALL.md` — created
- `docs/tasks/TASK-034-butler-uninstall.md` — created/modified

**Branch:** `git checkout task/034-butler-uninstall`
**Stage:** `git add src/butler_core/uninstall.py tests/test_uninstall.py src/butler_cli/__main__.py tests/test_cli.py Makefile README.md CHANGELOG.md REQUIREMENTS_UNINSTALL.md docs/tasks/TASK-034-butler-uninstall.md`
**Commit:** `git commit -m "Add butler-uninstall for removing butler from an adopting project"`
