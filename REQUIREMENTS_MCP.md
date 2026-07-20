# Requirements: Shared Task-Core, CLI, and MCP Server

## Context

python-butler currently expresses its task workflow (branch, stage, commit, PR,
merge) as `make` targets that parse `docs/tasks/TASK-<NNN>-*.md` files using
`grep`/`sed`. This works but has two limitations:

- The parsing logic exists only in shell, so any new consumer (an AI agent
  calling tools instead of shell commands, or a human preferring a CLI) must
  either shell out to `make` or reimplement the parsing.
- There is no structured way to read task state (status, acceptance criteria)
  without parsing markdown by hand.

This document specifies a shared Python core for task management, exposed
through three thin interfaces: the existing `make` targets, a new CLI, and a
new MCP server. All three must produce identical behavior, since they call
the same underlying functions.

## Goals

1. Implement task-file parsing and git/gh operations once, in a single Python
   package, callable from `make`, a CLI, and an MCP server.
2. Add task operations that do not exist today: listing tasks, reading a task
   as structured data, creating a new task from the template, and updating
   status or acceptance-criteria checkboxes.
3. Preserve full backward compatibility: existing `make` targets and the
   `docs/tasks/TASK-<NNN>-short-description.md` file format must keep working
   unchanged for projects that only adopt the Makefile.
4. Keep the MCP server and CLI optional additions. A project that only wants
   `make` must not be forced to install the new package.

## Non-goals

- Replacing `make` as the primary interface for existing adopters.
- Changing the task file format or the `task/<NNN>-short-description` branch
  naming convention.
- Building a web UI or any persistent server process (the MCP server is
  invoked via stdio by the calling agent, not run standalone).

## Architecture

```
adopting-project/
├── Makefile                  # includes .butler/Makefile, targets call the CLI
├── .butler/                  # butler subtree (Makefile only, after trim)
└── (butler_core installed as a dependency, e.g. via uv tool or project deps)

python-butler/
├── Makefile                  # existing make targets, refactored to call `butler-cli`
├── src/butler_core/          # shared package (parsing + git/gh operations)
│   ├── tasks.py              # Task dataclass, parse/read/write task files
│   ├── git_ops.py            # branch/stage/commit/pr/merge operations
│   └── __init__.py
├── src/butler_cli/           # CLI entry point, thin wrapper over butler_core
│   └── __main__.py
├── mcp/                      # MCP server, thin wrapper over butler_core
│   └── server.py
└── docs/tasks/                # unchanged
```

`butler_core` has no dependency on `make`, git subtree, or the adoption flow.
It operates on a `tasks_dir` path passed in by the caller (defaults to
`docs/tasks/`), so it works the same whether invoked from a fresh clone, an
adopting project, or a GitHub Codespace.

## Requirement 1: Task data model

**Description:** Provide a `Task` dataclass and a parser that reads a task
file into structured data, and a writer that renders a `Task` back to the
existing markdown format without altering unrelated content.

**Fields:** `id` (e.g. `TASK-015`), `title`, `status` (`todo` / `in-progress`
/ `done`), `description`, `branch_name`, `switch_create_cmd`, `stage_cmd`,
`commit_message`, `acceptance_criteria` (list of `{text, checked}`),
`completion` (optional: date, summary, files changed).

**Use case:** `requirements-drafter` or `implementation-worker` needs to read
a task's current acceptance criteria to decide whether the task is done.

```python
task = tasks.read_task("TASK-015", tasks_dir="docs/tasks")
assert task.status == "done"
assert all(c.checked for c in task.acceptance_criteria)
```

## Requirement 2: List and filter tasks

**Description:** A function that lists all tasks in `tasks_dir`, optionally
filtered by status, returning `Task` summaries without needing to read every
file into memory at once if not needed.

**Use case:** An agent asks "what tasks are still open?" and expects a
structured list back, not a raw directory listing.

```python
open_tasks = tasks.list_tasks(tasks_dir="docs/tasks", status="todo")
```

## Requirement 3: Create a new task

**Description:** Allocate the next `TASK-<NNN>` number, render the task
template with the supplied title/description, and write branch/stage/commit
fields in the exact format the existing `grep`/`sed` parsing in `Makefile`
expects (so `make branch-task`, `stage-task`, `commit-task` keep working on
tasks created via the CLI or MCP server).

**Use case:** `requirements-drafter` produces a confirmed requirement and
needs to persist it as a new task file, correctly numbered and formatted.

```python
task = tasks.create_task(
    title="Add butler-trim dry-run flag",
    description="...",
    tasks_dir="docs/tasks",
)
# writes docs/tasks/TASK-021-add-butler-trim-dry-run-flag.md
```

## Requirement 4: Update task status and acceptance criteria

**Description:** Functions to toggle a specific acceptance-criterion
checkbox and to change a task's `## Status` field, writing back only the
changed lines.

**Use case:** `implementation-worker` finishes implementing one acceptance
criterion and marks it done without needing to rewrite the whole file.

```python
tasks.check_criterion("TASK-021", index=2, tasks_dir="docs/tasks")
tasks.set_status("TASK-021", "done", tasks_dir="docs/tasks")
```

## Requirement 5: Git/gh operations module

**Description:** Extract the logic currently inline in `Makefile` targets
(`branch-task`, `stage-task`, `commit-task`, `pr-task`, `merge-pr`) into
Python functions operating on a `Task` object: `branch_for(task)`,
`stage_for(task)` (runs lint/format/pymarkdown fix, then `git add` per the
task's `Stage:` command), `commit_for(task)`, `open_pr_for(task)`,
`merge_pr_for(task)`.

**Constraint:** Behavior must match the current Makefile exactly, including
error messages (e.g. "No task file found matching '...'") so existing CI
scripts or muscle memory are not broken.

## Requirement 6: CLI

**Description:** A CLI (e.g. `butler-cli` or `butler`) exposing the above as
subcommands, installable independently of the MCP server.

```bash
butler task list --status todo
butler task show TASK-015
butler task create --title "..." --description "..."
butler task check TASK-015 --criterion 2
butler task branch TASK-015
butler task stage TASK-015
butler task commit TASK-015
butler task pr TASK-015
butler task merge TASK-015
```

**Use case:** A developer working in a terminal (including inside a GitHub
Codespace) who prefers direct commands over `make`, or a Windows environment
without `make` installed.

## Requirement 7: MCP server

**Description:** An MCP server (stdio transport by default) exposing the
same operations as tools, for use by Claude Code or any MCP-compatible
agent working inside the adopting project.

**Tools:**
- `list_tasks(status?)`
- `get_task(task_id)`
- `create_task(title, description)`
- `check_acceptance_criterion(task_id, index)`
- `set_task_status(task_id, status)`
- `branch_task(task_id)`
- `stage_task(task_id)`
- `commit_task(task_id)`
- `open_pr_for_task(task_id)`
- `merge_task_pr(task_id)`

**Constraint:** The server must not perform any action tools (branch, stage,
commit, PR, merge) without being explicitly invoked per call; no implicit
batching of multiple git operations behind a single tool call.

**Transport:** stdio only for v1. HTTP/SSE transport (for remote clients,
e.g. Claude Desktop reaching into a Codespace) is out of scope for this
spec and should be a separate follow-up requirement if needed.

## Requirement 8: Makefile refactor (backward compatible)

**Description:** Refactor existing `make` targets to call the CLI instead of
inlining `grep`/`sed` parsing, without changing target names, arguments
(`f=TASK-XXX`), or observable behavior.

```makefile
branch-task:
    @butler task branch $(f)

commit-task:
    @butler task commit $(f)
```

**Constraint:** If the CLI is not installed, targets must fail with a clear
error pointing at how to install it, not a cryptic Python traceback.

## Requirement 9: Packaging and optionality

**Description:** `butler_core` and `butler_cli` are published as a normal
Python package (installable via `uv`/`pip`) but are **not** required for a
project that only adopts butler's Makefile without the CLI or MCP server.
The MCP server depends on `butler_core` but is distributed separately (own
`pyproject.toml`, e.g. under `mcp/`) so its dependencies (MCP SDK) don't leak
into projects that don't use it.

**Scope note (no PyPI release required):** "Installable via `uv`/`pip`" in
this requirement means installable from the local source tree
(`uv tool install .` / `pip install .`) or from a Git URL
(`uv tool install git+https://...`). It does NOT imply publishing to PyPI,
maintaining a release/versioning process, or `pip install butler-cli`
resolving without a path/URL. A PyPI-published release is out of scope for
this requirement and would need its own future requirement (build/publish
pipeline, versioning scheme) if ever desired.

**Constraint (namespace collision):** The distribution name for the MCP
server package (currently `butler-mcp`) MUST NOT be `mcp`, since the server
depends on the official MCP SDK, which is itself published on PyPI as `mcp`.
Additionally, because the server's own source directory is named `mcp/` at
the repo root and contains no top-level `__init__.py`, it is susceptible to
being picked up as an implicit Python namespace package (PEP 420) if the
repo root ever ends up on `sys.path` (e.g. a script or test run from the
repo root, or a `PYTHONPATH` misconfiguration) in an environment where the
real `mcp` SDK is not installed. This would shadow the SDK import and
produce a confusing `ImportError`/`AttributeError` instead of a clear
"dependency not installed" error. Tooling and CI MUST invoke the MCP
server and its tests via `uv run` from inside `mcp/` (using its own
`.venv`), never from the repo root with the repo root on `sys.path`.

**Use case:** A developer runs `make branch-task` from the repo root while
the MCP server's dependencies aren't installed in that shell's environment.
The Makefile/CLI tooling must not accidentally attempt to `import mcp` from
repo-root context in a way that resolves to the local `mcp/` directory
instead of failing clearly or not attempting the import at all.

## Requirement 10: Bugfix — `merge-pr`/`merge-current-task` branch-name derivation

**Description:** `merge-pr` (Makefile) SHALL derive the task branch name by
reading the `**Branch name:**` line directly from the task file — the same
source `branch-task`, `stage-task`, `commit-task`, and `pr-task` already use
— instead of recomputing it from the task file's filename. The current `sed`
expression produces `task/task-<NNN>-<slug>` (with a duplicated `task-`
segment), which never matches the real branch convention `task/<NNN>-<slug>`,
so `make merge-pr`/`make merge-current-task` always fail with "No open PR for
branch ..." even when a valid, mergeable PR exists.

**Use case:** A developer or Workflow Guardian runs `make merge-current-task`
after a PR has been approved, expecting it to find and squash-merge the
correct PR without falling back to a manual `gh pr merge`.

```bash
make merge-current-task
# currently: "No open PR for branch task/task-025-mcp-server"
# expected: squash-merges the PR open on task/025-mcp-server
```

## Acceptance criteria (overall)

- [ ] `butler_core.tasks` provides `read_task`, `list_tasks`, `create_task`,
      `check_criterion`, `set_status`, all covered by Hypothesis-based tests
      for parsing edge cases.
- [ ] `butler_core.git_ops` provides `branch_for`, `stage_for`, `commit_for`,
      `open_pr_for`, `merge_pr_for`, matching current Makefile behavior.
- [ ] CLI installable via `uv tool install` and exposes all subcommands in
      Requirement 6.
- [ ] MCP server runs over stdio, exposes all tools in Requirement 7, and
      has been manually verified from Claude Code against a real adopting
      project's `docs/tasks/`.
- [ ] Existing `make branch-task`, `stage-task`, `commit-task`, `pr-task`,
      `merge-pr` targets (and their `-current-task` variants) still work
      unchanged from an adopting project's perspective.
- [ ] `make lint && make test` pass in the butler repo.
- [ ] README documents installation and usage of the CLI and MCP server as
      optional additions, separate from the base Makefile adoption flow.
