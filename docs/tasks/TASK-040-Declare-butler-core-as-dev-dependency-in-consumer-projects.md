# TASK-040: Declare butler-core as a dev dependency in consumer projects

## Status

Draft

## Background

The `butler` CLI and MCP server ship in the `butler-core` package. Today the
package is installed manually into the consumer project's venv, e.g.:

```
uv pip install --force-reinstall .butler/
```

This has two problems:

1. **`uv sync` removes it.** butler-core is not declared in the consumer's
   `pyproject.toml`/`uv.lock`, so any `uv sync` (including `make install`,
   which runs `uv sync --extra dev`) uninstalls it. The CLI silently
   disappears until someone reinstalls it manually.
2. **Path installs break after trim.** Installing from `.butler/` couples the
   installed package to subtree sources that `butler-trim` deletes. A
   non-editable install survives, but any resolver re-check against the path
   source fails once the sources are gone.

The robust model is to declare butler-core as a dev dependency with a git
source, so uv owns the installation, the version is pinned in `uv.lock`, and
`.butler/` trimming is irrelevant to the CLI.

## Goal

Consumer projects shall get butler-core installed and kept in sync by uv,
declared as a dev dependency with a git source. Butler's install and scaffold
targets shall set this up automatically, and updating butler shall update the
locked butler-core version.

## Approach

1. **Scaffold:** add butler-core to the dev dependency group in
   `scaffold/pyproject.toml.tmpl`:

   ```toml
   [dependency-groups]
   dev = [
       "butler-core @ git+https://github.com/CmdrPrompt/python-butler.git",
   ]
   ```

   Source the URL from `BUTLER_REMOTE` so forks resolve to their own remote.
2. **Existing projects:** add a target (e.g. `butler-install-cli`) that inserts
   the dependency into an existing `pyproject.toml` if missing, then runs
   `uv lock --upgrade-package butler-core && uv sync`. Idempotent: if already
   declared, only upgrade and sync.
3. **`make install`:** call `butler-install-cli` (or verify the declaration)
   so a fresh clone gets a working CLI without manual steps.
4. **`butler-pull`:** after pulling the subtree, run
   `uv lock --upgrade-package butler-core && uv sync` instead of the
   `uv pip install .butler/` step planned in TASK-NNN (conflict-free
   butler-pull). Update that task to reference this model.
5. **`check-butler`:** update the error message to point at
   `make butler-install-cli` instead of `uv pip install -e .`.
6. **Docs:** update README install and update sections accordingly.

## Requirements

- R1: `scaffold/pyproject.toml.tmpl` shall declare butler-core as a dev
  dependency with a git source derived from `BUTLER_REMOTE`.
- R2: A make target shall add the butler-core dev dependency to an existing
  `pyproject.toml` if missing, lock, and sync. Running it twice shall be a
  no-op apart from lock/sync.
- R3: After `make install` in a project set up per R1 or R2, the `butler` CLI
  and MCP entry points shall be runnable from the project venv.
- R4: `uv sync` shall never remove butler-core in a project set up per R1/R2.
- R5: `butler-pull` shall upgrade the locked butler-core version to match the
  pulled butler revision (`uv lock --upgrade-package butler-core` + sync) and
  shall not install from the `.butler/` path.
- R6: No target shall perform an editable or path-based install of butler-core
  from `.butler/`.
- R7: `check-butler`'s error message shall reference the new install target and
  the package name butler-core.
- R8: Projects that adopted butler before butler-core existed (Makefile-only)
  shall not break: targets that need the CLI keep failing via `check-butler`
  with the updated guidance, and all other targets work unchanged.

## Acceptance criteria

- AC1: New project via scaffold: `make install`, then `butler --help` succeeds
  and `uv pip show butler-core` reports a site-packages location.
- AC2: Existing project without the declaration: run the new target, verify
  `pyproject.toml` gained the dev dependency, `uv.lock` contains butler-core
  with a git source, and `butler --help` succeeds. Run the target again:
  `pyproject.toml` unchanged.
- AC3: Run `uv sync --extra dev` after AC1/AC2: butler-core is still installed.
- AC4: Run `make butler-trim`, then `butler --help`: still succeeds.
- AC5: Push a version bump to a local bare butler remote, run `make butler-pull`
  in the consumer: `uv.lock` records the new butler-core version and
  `butler --version` (or equivalent) reports it.
- AC6: Grep the Makefile: no occurrence of `pip install` targeting `.butler/`
  and no `-e` install of butler-core.

## Out of scope

- Publishing butler-core to PyPI.
- The subtree merge-conflict fix itself (TASK-NNN, conflict-free butler-pull);
  this task only replaces its CLI reinstall step.
- Support for non-uv package managers.

## Notes

- Coordinate with TASK-NNN (conflict-free butler-pull): implement this task
  first or together, then simplify that task's approach step 4 and R7 to R9 to
  reference lock/sync instead of `uv pip install .butler/`.
- Editing `pyproject.toml` from make: prefer a small Python helper (tomllib
  read, targeted insert) over sed to avoid corrupting user files; fail with a
  clear message if the file cannot be parsed.
- `uv lock --upgrade-package` against a git source re-resolves the commit for
  the tracked branch; verify behavior when `BUTLER_REMOTE` is a local path in
  tests (uv supports `git+file://` URLs).
- Update CHANGELOG.md.