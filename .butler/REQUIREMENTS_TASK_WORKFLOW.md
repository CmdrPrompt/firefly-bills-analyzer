# Requirements: Task Workflow (`butler task` <-> vendored Makefile)

## Context

python-butler ships two entry points for the task-branch workflow that
CLAUDE.md mandates: the `butler` CLI (`butler task branch|stage|commit|pr|merge`,
backed by `src/butler_core/git_ops.py`) and a set of `make` targets
(`branch-task`, `stage-task`, `commit-task`, `pr-task`, `merge-pr`, and their
`*-current-task` wrappers) defined in this repo's root `Makefile`, which is
vendored unchanged into adopting projects as `.butler/Makefile` via
`git subtree add --prefix=.butler`.

TASK-043 documents a real-world incident in a consumer project
(`firefly-python-api`): running `make branch-task` recursed infinitely, and
a `--tasks-dir` flag the vendored Makefile passed was rejected by the
installed CLI. Investigation traced this to a **stale vendored
`.butler/Makefile` snapshot** in that consumer project, predating the
TASK-022/023 refactor that introduced `src/butler_core/git_ops.py` as the
single, correct implementation of branch/stage/commit/pr/merge logic. This
repo's *current* source was never broken: `git_ops.py` was built from day
one (TASK-023, 2026-07-08) to hold the real implementation, the current root
`Makefile` already calls `butler --tasks-dir $(TASKS_DIR) task <cmd> $(f)`
exactly once with no callback, and the CLI already accepts `--tasks-dir`.
There is no history of a `butler/commands/task.py`-style proxy-to-Makefile
implementation anywhere in this repo.

The real, unresolved problem is that once a consumer project vendors
`.butler/Makefile` via `git subtree add`, nothing keeps that copy in sync
with this repo going forward. A consumer can end up pinned to an old,
structurally-different snapshot indefinitely, with no supported way to
detect or correct the drift short of manually diffing and patching files —
exactly what happened to `firefly-python-api`. This document formalizes the
architecture that already exists here (so it cannot silently regress) and
defines the missing piece: a way for consumer projects to refresh their
vendored Makefile.

## Goals

1. Formalize, via regression tests, that `butler task <cmd>` (backed by
   `butler_core.git_ops`) remains the single source of truth for branch
   create/switch, stage, commit, PR open, and PR merge logic, and that
   `.butler/Makefile` task targets remain thin, non-recursive wrappers.
2. Guard against future flag drift (e.g. `--tasks-dir`) between the vendored
   Makefile and the installed CLI's argument parser.
3. Give consumer projects a command to refresh their vendored
   `.butler/Makefile` to match the currently installed CLI/package version,
   so a project can never again get permanently stuck on a stale, buggy
   snapshot the way `firefly-python-api` did.

## Non-goals

- Fixing this repo's own `butler_core`/`butler_cli`/`Makefile` source code —
  it already implements the correct non-recursive architecture and already
  accepts `--tasks-dir`. No bug fix is needed here; only regression-proofing
  and a distribution-refresh mechanism.
- Fixing already-vendored `.butler/Makefile` copies in existing consumer
  repos (e.g. `firefly-python-api`) directly from this repo — out of scope
  per TASK-043; those projects pick up the fix by running the new refresh
  command (Requirement 3) themselves once it ships.
- Changing the subtree-based adoption mechanism itself (`git subtree add`) —
  only refreshing the Makefile file within an already-adopted project is in
  scope.

## Requirement 1: Regression test protecting the non-recursive architecture

**Description:** An automated test MUST exist that fails if the
non-recursive architecture ever regresses: `butler_core.git_ops`'s
branch/stage/commit/pr/merge functions (`branch_for`, `stage_for`,
`commit_for`, `open_pr_for`, `merge_pr_for`) MUST NOT construct a
`subprocess` call whose first argument is `"make"`, and an end-to-end test
running `butler task branch` (and the other four subcommands) in a fixture
project MUST assert the process completes without spawning a nested
`butler` or `make` process. This formalizes and protects behavior that
already exists in this repo's source as of TASK-023 — it is not new
implementation, only new test coverage.

**Use case:**

```python
def test_git_ops_never_shells_out_to_make():
    """Regression test for TASK-043: butler_core.git_ops must never proxy
    back to `make` for branch/stage/commit/pr/merge operations, and the
    vendored Makefile must never be able to recurse into itself through
    the CLI."""
    ...
```

## Requirement 2: Guard against `--tasks-dir` (and future flag) drift

**Description:** A dedicated automated test MUST parse the `butler ...`
invocations in the root `Makefile` and cross-check every flag they pass
(currently `--tasks-dir`) against the CLI's argparse definition
(`src/butler_cli/__main__.py`), failing if any flag the Makefile passes is
not accepted by the installed CLI. This test MUST run as part of
`make test`. This already holds today — the requirement is to keep it
enforced automatically going forward, so a future change to the CLI's
task-directory configuration mechanism (e.g. a move to a config file) cannot
ship without a matching update to the vendored Makefile's `butler`
invocations in the same commit/PR, or without a documented deprecation
window if the old flag is kept for compatibility.

**Use case:**

```bash
make test
# includes a dedicated test that parses every `butler ...` invocation in
# the root Makefile, extracts the flags passed, and asserts each flag is
# accepted by src/butler_cli/__main__.py's argparse definition; fails the
# build if a flag is dropped from one side without the other being
# updated in the same change.
```

## Requirement 3: `butler` command to refresh a consumer project's vendored Makefile

**Description:** A CLI command, `butler sync`, MUST be able to overwrite a
consumer project's `.butler/Makefile` with the version bundled in the
currently installed `butler` package, so that a consumer project can correct
drift between its vendored Makefile and the installed CLI (such as the
stale snapshot `firefly-python-api` was pinned to) without manually diffing
and patching files by hand. `butler sync --dry-run` MUST compare the actual
content (e.g. hash or diff) of the local `.butler/Makefile` against the
bundled version and report a needed change only if they actually differ —
it MUST NOT unconditionally report "would overwrite" regardless of content.
The command MUST refuse to run on a dirty working tree unless `--force` is
passed (consistent with `REQUIREMENTS_UNINSTALL.md` Requirement 3), and MUST
support `--dry-run`.

**Use case:**

```bash
butler sync --dry-run
# Compares the content (hash/diff) of the local .butler/Makefile against
# the version bundled in the installed butler package.
# If they differ:
#   would overwrite .butler/Makefile (local hash abc123 != bundled hash def456)
# If they are identical:
#   .butler/Makefile is already up to date; nothing to do

butler sync
# overwrites .butler/Makefile with the version bundled in the installed
# butler package, only if its content differs from the bundled version;
# leaves other vendored files (governance docs, agents) untouched
```

## Acceptance criteria (overall)

- [ ] A regression test exists asserting `butler_core.git_ops` never shells
      out to `make`, and that `butler task <cmd>` end-to-end does not spawn
      a nested `butler`/`make` process.
- [ ] A dedicated automated test exists (run in `make test`) that parses
      every `butler` flag used in the root Makefile and asserts it is
      accepted by the CLI's argparse definition, failing the build on
      drift.
- [ ] `butler sync` can refresh a consumer project's `.butler/Makefile` to
      match the installed CLI version, comparing content (hash/diff) to
      decide whether a change is needed, gated by a clean-working-tree
      check (`--force` to override), and supporting `--dry-run`.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
