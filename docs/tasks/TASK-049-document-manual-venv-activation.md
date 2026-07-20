# TASK-049 Document manual `.venv` activation in `make help` / README

## Status

todo

## Description

A consumer asked whether butler's distributed `Makefile` could gain a target
like `make activate` that runs `source .venv/bin/activate`, to avoid typing
the full path by hand.

This is not implementable as a plain Make target: every recipe line runs in
its own subprocess, so `source .venv/bin/activate` inside a `make` recipe only
modifies that subprocess's environment — it has no effect on the interactive
shell the user invoked `make` from. `make activate` would exit having done
nothing observable, which is worse than no target at all (looks like it
worked, doesn't).

Butler's own convention already sidesteps the need to activate at all — every
target in the distributed `Makefile` uses `uv run <command>` instead of
assuming an active venv (see `lint`, `test`, `install`, etc.). So for anything
butler itself runs, activation is a non-issue.

What's missing is guidance for consumers who *do* want an activated shell
(e.g. to run a project binary directly, or use editor tooling that expects
`$VIRTUAL_ENV`). Two additive, low-risk options, not mutually exclusive:

1. Add a line to `make help`'s "First time on a new machine" section pointing
   at the standard command: `source .venv/bin/activate`.
2. Document, in the README's adoption guide, a `~/.zshrc` / `~/.bashrc` shell
   function consumers can add once, e.g.:
  
```sh
   activate() {
     if [ -f .venv/bin/activate ]; then source .venv/bin/activate
     else echo "No .venv/bin/activate found in $(pwd)"; fi
   }
   ```
  
This works because it runs as a function in the caller's own shell, not a
   Make subprocess.

No new Make target should be added that silently does nothing when it fails
to activate anything.

## Branch

**Branch name:** `task/049-document-manual-venv-activation`
**Switch/create:** `git checkout -b task/049-document-manual-venv-activation`
**Make target:** `make branch-task f=TASK-049`

## Acceptance criteria

- [ ] `make help`'s "First time on a new machine" section documents
      `source .venv/bin/activate` as the way to activate the venv in the
      current shell
- [ ] README's adoption guide includes the optional `activate` shell function
      snippet above, with a one-line note on *why* it must be a shell
      function and not a Make target
- [ ] No new Make target is added for activation
- [ ] `CHANGELOG.md` updated

## Completion

**Date:**
**Summary:**
**Files changed:**

- `Makefile` — modified (`help` target text)
- `README.md` — modified (adoption guide)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-049-document-manual-venv-activation.md` — modified

**Branch:** `git checkout task/049-document-manual-venv-activation`
**Stage:** `git add Makefile README.md CHANGELOG.md docs/tasks/TASK-049-document-manual-venv-activation.md`
**Commit:** `git commit -m "Document manual .venv activation in make help and README (TASK-049)"`
