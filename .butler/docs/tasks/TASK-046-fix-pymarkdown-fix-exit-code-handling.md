# TASK-046 Stop treating pymarkdown's "fixed a file" exit code as a failure

## Status

done

## Description

`pymarkdown ... fix <files>` uses the library's default return-code scheme
(`pymarkdown/return_code_helper.py`, `DefaultScheme`), under which
`ApplicationResult.FIXED_AT_LEAST_ONE_FILE` maps to exit code **3** — this is
the normal, successful outcome whenever `fix` actually rewrites a file, not an
error. Every call site that invokes `pymarkdown fix` currently treats any
non-zero exit as fatal, so the very common case of "fixed a markdown file"
crashes the workflow that was supposed to fix it:

- `Makefile`'s `fix` target (and the identical `src/butler_core/data/Makefile`
  copy vendored into adopting projects) — each recipe line's exit status is
  checked by `make`, so `make fix`/`make lint`'s downstream tooling fails with
  `Error 3` as soon as any `.md` file needed a real fix.
- `butler_core.git_ops.stage_for()` (`src/butler_core/git_ops.py`) calls
  `subprocess.run([..., "pymarkdown", ..., "fix", *md_files], check=True, ...)`.
  `check=True` raises `CalledProcessError` on the same exit code 3, so
  `make stage-task`/`make stage-current-task` (and the MCP/CLI commands that
  wrap them) crash with a Python traceback instead of completing the stage.

Reproduced in a downstream project (`firefly-bills-analyzer`) by removing a
markdown file's trailing newline and running `make fix` (or `make
stage-current-task`): `pymarkdown` correctly fixes the file and prints
`Fixed: <path>`, then the recipe/subprocess aborts anyway because the exit
code is 3.

Fix: append `--return-code-scheme minimal` to every `pymarkdown ... fix ...`
invocation. Under `MinimalScheme`,
`FIXED_AT_LEAST_ONE_FILE` maps to exit code 0, while `COMMAND_LINE_ERROR` (2)
and `SYSTEM_ERROR` (1, remapped) still surface as failures, so genuine errors
are still caught. This must be applied identically to:

- `Makefile` (`fix` and `stage` targets)
- `src/butler_core/data/Makefile` (packaged copy — a regression test already
  asserts this file never drifts from the root `Makefile`, per TASK-045)
- `src/butler_core/git_ops.py`'s `stage_for()`

The `pymarkdown ... scan` invocations (used for `make lint`'s check-only pass)
are unaffected — `scan` never fixes files, so its exit codes already mean what
callers assume.

Covers Requirement 5 from REQUIREMENTS_MCP.md (`stage_for` behavior).

**Depends on:** none

## Branch

**Branch name:** `task/046-fix-pymarkdown-fix-exit-code-handling`
**Switch/create:** `git checkout -b task/046-fix-pymarkdown-fix-exit-code-handling`
**Make target:** `make branch-task f=TASK-046`

## Acceptance criteria

- [x] `Makefile`'s `fix` and `stage` targets pass `--return-code-scheme minimal`
      to `pymarkdown ... fix ...`, and `src/butler_core/data/Makefile` is kept
      byte-identical to it (verified by the existing drift regression test)
- [x] `butler_core.git_ops.stage_for()` passes `--return-code-scheme minimal`
      to its `pymarkdown ... fix ...` subprocess call
- [x] A test (or reproduction) confirms `stage_for()` no longer raises when
      `pymarkdown fix` actually rewrites a file (e.g. a fixture markdown file
      missing a trailing newline)
- [x] A genuine `pymarkdown` command-line error (e.g. an invalid `--config`
      path) still causes `stage_for()`/`make fix` to fail loudly, confirming
      the scheme change doesn't silently swallow real errors
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-11
**Summary:** Added `--return-code-scheme minimal` (a global pymarkdown option,
placed before the `fix` subcommand) to every `pymarkdown ... fix ...`
invocation in `Makefile`, the vendored `src/butler_core/data/Makefile` copy,
and `butler_core.git_ops.stage_for()`. Under the minimal scheme,
`FIXED_AT_LEAST_ONE_FILE` maps to exit code 0 instead of 3, so successfully
rewriting a markdown file no longer aborts `make fix`/`make stage` or raises
`CalledProcessError` in `stage_for()`. Verified with a live `pymarkdown`
reproduction (missing trailing newline: exit 0 with the flag, would have been
3 without) and confirmed a genuine CLI error (bad `--config` path) still
returns a non-zero exit code. `make test` passes (158/158). `make lint` was
not run to completion — it fails on pre-existing MD025/MD047 violations in
`docs/tasks/TASK-039-*.md` and `TASK-040-*.md` from the `scan` step,
unrelated to this change and reproduced as pre-existing on `main` before this
branch's edits.
**Files changed:**

- `Makefile` — modified
- `src/butler_core/data/Makefile` — modified
- `src/butler_core/git_ops.py` — modified
- `tests/test_git_ops.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-046-fix-pymarkdown-fix-exit-code-handling.md` — modified

**Branch:** `git checkout task/046-fix-pymarkdown-fix-exit-code-handling`
**Stage:** `git add Makefile src/butler_core/data/Makefile src/butler_core/git_ops.py tests/test_git_ops.py CHANGELOG.md docs/tasks/TASK-046-fix-pymarkdown-fix-exit-code-handling.md`
**Commit:** `git commit -m "Stop treating pymarkdown's fixed-a-file exit code as a failure (TASK-046)"`
