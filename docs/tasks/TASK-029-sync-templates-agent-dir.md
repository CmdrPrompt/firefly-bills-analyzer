# TASK-029 Sync templates/ agent set with .claude/agents/

## Status

done

## Description

`templates/` is the Copilot-facing counterpart of `claude-agents/`/`.claude/agents/`:
`make generate-governance-files` renders `templates/*.agent.md.tmpl` (substituting
`{{REQUIREMENTS_PATH}}` etc.) into an adopting project's `.github/agents/` (Makefile:401-405).
It has drifted from `.claude/agents/`, which is the up-to-date, actively-used set (per
TASK-028's precedent of treating `.claude/agents/` as the source of truth):

- `templates/test-design-reviewer.agent.md.tmpl` and `templates/test-writer.agent.md.tmpl`
  are missing entirely, even though `.claude/agents/test-design-reviewer.agent.md` and
  `.claude/agents/test-writer.agent.md` exist and are part of the current workflow (the
  Test Design Reviewer gate added in TASK-028).
- The `for agent in ...` loop in `generate-governance-files`
  (Makefile:401) does not list `test-design-reviewer` or `test-writer`, so even with the
  `.tmpl` files added, the generator would not produce `.github/agents/` copies of them.

This task adds the two missing `.tmpl` files, following the established Copilot-template
conventions (generated-from header comment, VS Code chat-mode `tools:` list instead of
Claude tool names, no `name:`/`argument-hint:`/`user-invocable:` frontmatter, no
worktree-isolation "Execution context" section, `{{REQUIREMENTS_PATH}}` substitution where
the Claude source references "the project's requirements document"), and adds both agents
to the Makefile generation loop.

## Branch

**Branch name:** `task/029-sync-templates-agent-dir`
**Switch/create:** `git checkout -b task/029-sync-templates-agent-dir`
**Make target:** `make branch-task f=TASK-029`

## Acceptance criteria

- [x] `templates/test-design-reviewer.agent.md.tmpl` exists, following the same
      frontmatter/structure conventions as the other `templates/*.agent.md.tmpl` files
- [x] `templates/test-writer.agent.md.tmpl` exists, same conventions
- [x] Both agents are added to the `for agent in ...` loop in `generate-governance-files`
      (Makefile) so `.github/agents/test-design-reviewer.agent.md` and
      `.github/agents/test-writer.agent.md` are generated
- [x] `make lint && make test` pass
- [x] CHANGELOG.md updated

## Completion

**Date:** 2026-07-08
**Summary:** Added `templates/test-design-reviewer.agent.md.tmpl` and
`templates/test-writer.agent.md.tmpl`, rewritten from their `.claude/agents/` counterparts
per the established Copilot-template conventions (generated-from header comment, VS Code
chat-mode `tools:` list, no `name:`/`argument-hint:`/`user-invocable:` frontmatter, no
worktree-isolation "Execution context" section). Added both agent names to the
`for agent in ...` loop in `generate-governance-files` (Makefile) so
`make generate-governance-files` now also produces `.github/agents/test-design-reviewer.agent.md`
and `.github/agents/test-writer.agent.md` in adopting projects. Verified by running
`generate-governance-files` against a scratch copy of the repo and confirming both files
appear in the generated `.github/agents/`. No new test files were added (this task changes
static template/config content, not application behavior), so the Test Design Reviewer gate
does not apply. `make lint && make test` pass.
**Files changed:**

- `templates/test-design-reviewer.agent.md.tmpl` — created
- `templates/test-writer.agent.md.tmpl` — created
- `Makefile` — modified (added both agents to generate-governance-files loop)
- `CHANGELOG.md` — modified (Fixed entry)

**Branch:** `git checkout task/029-sync-templates-agent-dir`
**Stage:** `git add templates/test-design-reviewer.agent.md.tmpl templates/test-writer.agent.md.tmpl Makefile CHANGELOG.md docs/tasks/TASK-029-sync-templates-agent-dir.md`
**Commit:** `git commit -m "Add missing test-design-reviewer and test-writer templates to templates/ (TASK-029)"`
