# TASK-039: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.

# TASK-NNN: Conflict-free butler-pull with CLI upgrade

## Status

Draft

## Background

Two related problems in `make butler-pull`:

**1. Merge conflicts after trim.** `make butler-trim` deletes everything in
`.butler/` except `Makefile`. When upstream python-butler later modifies any of
the trimmed files, `git subtree pull --squash` runs against a working tree where
those files no longer exist. Git reports modify/delete conflicts, the merge
fails, and the user must resolve it manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will
hit it on every update that touches a trimmed file.

**2. Stale CLI after pull.** The `butler` CLI (and MCP server) is installed as a
package in the project venv, while `butler-pull` only updates the subtree. After
a pull the installed CLI can lag behind the pulled sources, and once
`butler-trim` has run the new sources are gone, so upgrading requires a manual
`butler-fetch` first. `butler-pull` should reinstall the CLI from the freshly
pulled sources before trimming.

## Goal

`make butler-pull` shall, in a project that has previously run `make butler-trim`
and has no local edits inside `.butler/`:

1. Complete without merge conflicts.
2. Leave the installed `butler` CLI (and MCP server entry points) matching the
   pulled butler version.

## Approach

Restore trimmed files before pulling, reinstall the CLI from the pulled sources,
then trim:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REMOTE> main --squash`.
4. Reinstall the CLI non-editable from the pulled sources:
   `uv pip install --force-reinstall .butler/`
   (guard: skip with a notice if no venv is active/present, or if `.butler/`
   contains no installable package, to stay backward compatible with
   Makefile-only consumers).
5. Run the existing trim logic (reuse `butler-trim`).
6. Update `.butler-version` as today.

Reuse: `butler-fetch` conceptually restores butler sources. Extract the restore
step into a shared internal target (e.g. `_butler-restore`) used by both
`butler-fetch` and `butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.
- R7: After `make butler-pull`, the installed `butler` CLI shall be built from
  the pulled butler sources (non-editable install), so it keeps working after
  trim and matches the version recorded in `.butler-version`.
- R8: If no virtual environment is available or `.butler/` contains no
  installable package, `butler-pull` shall skip the CLI reinstall with an
  informative notice and still complete the pull and trim successfully.
- R9: `butler-pull` shall never perform an editable (`-e`) install from
  `.butler/`.
- R10: `check-butler`'s error message shall instruct users to install the CLI
  non-editable (from the butler repo or via `butler-pull`), not editable from
  `.butler/`.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to
  a trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree
  untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.
- AC6: With an active venv and an installable package in butler: after
  `make butler-pull`, `butler --version` (or equivalent) reports the pulled
  version, and the CLI still runs after `.butler/` has been trimmed.
- AC7: Without a venv (or with a Makefile-only butler checkout):
  `make butler-pull` exits 0, prints a notice that the CLI reinstall was
  skipped, and pull plus trim are completed.
- AC8: `uv pip show` for the installed package reports a site-packages
  location, not a path under `.butler/`.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.
- Publishing the CLI to PyPI or supporting git-URL installs in `butler-pull`
  (users can still do this manually).

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in
  tests.
- Update `README.md` sections "Keeping butler up to date" and the CLI install
  instructions to reflect the non-editable install and the automatic reinstall
  in `butler-pull`.
- MCP server entry points ship in the same package as the CLI, so R7 covers
  them; verify any MCP client configuration examples in docs do not reference
  paths under `.butler/`.
- Add a CHANGELOG.md entry.