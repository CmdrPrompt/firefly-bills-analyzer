# TASK-020 Clarify agent invocation context in Workflow Guardian

## Status

done

## Description

Add an "Invocation Context" section to the Workflow Guardian agent files explaining
that a `@` mention in Claude Code means Claude acts as the agent in the main
conversation — it must not spawn another Workflow Guardian. After requirements
confirmation it should spawn Implementation Worker (not itself) for coding.

Affects three source files:
- `claude-agents/workflow-guardian.agent.md` → distributed to `.claude/agents/`
- `templates/workflow-guardian.agent.md.tmpl` → rendered to `.github/agents/`
- `.claude/agents/workflow-guardian.agent.md` — python-butler's own agent copy

## Branch

**Branch name:** `task/020-clarify-agent-invocation`
**Switch/create:** `git checkout -b task/020-clarify-agent-invocation`
**Make target:** `make branch-task f=TASK-020`

## Acceptance criteria

- [x] `claude-agents/workflow-guardian.agent.md` has "Invocation Context" section
- [x] `templates/workflow-guardian.agent.md.tmpl` has "Invocation Context" section
- [x] `.claude/agents/workflow-guardian.agent.md` has "Invocation Context" section

## Completion

**Date:** 2026-05-12
**Summary:** Added "Invocation Context" section to all three Workflow Guardian source files. Explains that @-mention in Claude Code means Claude acts as the agent directly and should spawn Implementation Worker (not another Workflow Guardian) for the coding phase.
**Files changed:**

- `claude-agents/workflow-guardian.agent.md` — modified
- `templates/workflow-guardian.agent.md.tmpl` — modified
- `.claude/agents/workflow-guardian.agent.md` — modified
- `docs/tasks/TASK-020-clarify-agent-invocation.md` — created

**Branch:** `git checkout task/020-clarify-agent-invocation`
**Stage:** `git add claude-agents/workflow-guardian.agent.md templates/workflow-guardian.agent.md.tmpl .claude/agents/workflow-guardian.agent.md docs/tasks/TASK-020-clarify-agent-invocation.md`
**Commit:** `git commit -m "Clarify agent invocation context in Workflow Guardian"`
