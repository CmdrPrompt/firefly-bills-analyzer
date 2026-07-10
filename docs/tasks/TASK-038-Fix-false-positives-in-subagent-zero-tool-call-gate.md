# TASK-038 Fix false positives in subagent zero-tool-call gate

## Status

done

## Description

The subagent hard gate introduced in TASK-035 fires on any subagent turn that
ends with zero `tool_use` blocks, on the assumption that this always indicates
broken `tools:` frontmatter. Two incidents since then show the heuristic is
too blunt:

1. **False positive on legitimately tool-free work.** Test Design Reviewer
   (`a92da30e8a38f59e8`) was deliberately briefed with all code content pasted
   into the prompt and instructed not to read files. It delivered a complete,
   valid review report (Farley Index 8.6/10) with zero tool calls, and
   `make validate-agents` confirmed all definitions valid (9/9). The gate
   still fired and instructed the coordinator to stop until validate-agents
   passes, a condition that was already satisfied, making the directive
   incoherent.
2. **Orphaned markers across sessions.** A marker written in one session
   tripped the gate in a later, unrelated session, because markers carry no
   session identity and the gate consumes every marker it finds.

Fix in three parts:

1. **Corroborating-evidence heuristic** in `subagent_toolcheck.py`: flag only
   when zero `tool_use` blocks coincide with at least one signature of the
   real failure mode. Signatures, any one sufficient: (a) an assistant text
   block matching a tool-narration pattern (a bare tool-name token followed by
   a JSON object, or a response consisting solely of a JSON object of tool
   arguments), or (b) a coordinator follow-up message in the transcript
   (`isMeta: true` with `origin.kind == "coordinator"`), which indicates the
   coordinator already observed a stalled turn. A long free-text final report
   with zero tool calls must NOT trigger.
2. **Per-agent opt-out**: new frontmatter key `allow-tool-free: true` for
   agents whose task is pure text-in/text-out (Test Design Reviewer).
   `validate_agents.py` accepts the key and validates it as boolean;
   `subagent_toolcheck.py` reads the agent definition (resolved from
   `agent_type`) and skips the check entirely when set.
3. **Session-scoped markers**: `subagent_toolcheck.py` writes `session_id`
   into each marker; `agent_result_gate.py` consumes only markers matching
   its own `session_id` from stdin, and deletes markers older than 24 hours
   regardless of session to prevent accumulation.

**Depends on:** TASK-035

## Branch

**Branch name:** `task/038-gate-false-positives`
**Switch/create:** `git checkout -b task/038-gate-false-positives`
**Make target:** `make branch-task f=TASK-038`

## Acceptance criteria

- [x] Replaying the Test Design Reviewer transcript (`a92da30e8a38f59e8`, zero tool calls, long report) through `subagent_toolcheck.py` writes NO marker
- [x] Replaying the TASK-034 failure transcripts (Test Writer `a58422292d7c45fdf`, PR Reviewer `a01168c9db255b431`) still writes markers (regression guard for both signature types: narration pattern and coordinator follow-up)
- [x] `test-design-reviewer.agent.md` declares `allow-tool-free: true`; `subagent_toolcheck.py` skips agents with the flag; `validate_agents.py` accepts the key and rejects non-boolean values
- [x] Markers include `session_id`; `agent_result_gate.py` ignores markers from other sessions and prunes markers older than 24h
- [x] The gate's stderr directive no longer unconditionally claims a frontmatter error: when `validate-agents` passes, the message states that configuration is valid and points to the transcript and marker diagnosis instead
- [x] Unit tests cover: tool-free-with-report (no trigger), narration pattern (trigger), coordinator follow-up (trigger), opt-out flag (no trigger), cross-session marker (ignored), stale marker (pruned)
- [x] README's "Agent configuration validation" section documents `allow-tool-free` and the refined heuristic
- [x] CHANGELOG has a Fixed entry under Unreleased (TASK-038)
- [x] `make validate-agents && make lint && make test` pass

## Files

- `.claude/hooks/subagent_toolcheck.py` — modified (evidence heuristic, opt-out, session_id)
- `.claude/hooks/agent_result_gate.py` — modified (session scoping, pruning, message wording)
- `scripts/validate_agents.py` — modified (allow-tool-free key)
- `.claude/agents/test-design-reviewer.agent.md` — modified (allow-tool-free: true)
- `claude-agents/test-design-reviewer.agent.md` — modified (synced)
- `tests/test_subagent_gate.py` — created
- `README.md` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-038-gate-false-positives.md` — created

**Branch:** `git checkout task/038-gate-false-positives`
**Stage:** `git add .claude/hooks/ scripts/validate_agents.py .claude/agents/test-design-reviewer.agent.md claude-agents/test-design-reviewer.agent.md tests/test_subagent_gate.py README.md CHANGELOG.md docs/tasks/TASK-038-gate-false-positives.md`
**Commit:** `git commit -m "Fix false positives in subagent zero-tool-call gate"`

## Completion

**Date:** 2026-07-09
**Summary:** Replaced the blunt "zero tool calls == broken frontmatter" heuristic with a
corroborating-evidence check (tool-narration text pattern or a coordinator follow-up event)
so a legitimately tool-free subagent report no longer trips the gate. Added a per-agent
`allow-tool-free: true` opt-out (declared on Test Design Reviewer, both copies) validated by
`scripts/validate_agents.py`. Markers now carry `session_id`; `agent_result_gate.py` only
treats same-session markers as trigger candidates (cross-session markers are left in place)
and prunes any marker older than 24 hours regardless of session, independent of the existing
60-minute same-session staleness behavior. The gate's stderr directive no longer
unconditionally claims a frontmatter configuration error: when `validate-agents` passes it
now states the configuration is valid and points at the transcript/marker diagnosis instead.
**Files changed:** `.claude/hooks/subagent_toolcheck.py`, `.claude/hooks/agent_result_gate.py`,
`scripts/validate_agents.py`, `.claude/agents/test-design-reviewer.agent.md`,
`claude-agents/test-design-reviewer.agent.md`, `tests/test_subagent_gate.py` (new),
`tests/test_hooks.py`, `tests/test_validate_agents.py`, `README.md`, `CHANGELOG.md`,
`docs/tasks/TASK-038-Fix-false-positives-in-subagent-zero-tool-call-gate.md`
**Branch:** `task/038-gate-false-positives`
**Stage:** `git add .claude/hooks/subagent_toolcheck.py .claude/hooks/agent_result_gate.py scripts/validate_agents.py .claude/agents/test-design-reviewer.agent.md claude-agents/test-design-reviewer.agent.md tests/test_subagent_gate.py tests/test_hooks.py tests/test_validate_agents.py README.md CHANGELOG.md docs/tasks/TASK-038-Fix-false-positives-in-subagent-zero-tool-call-gate.md`
**Commit:** `git commit -m "Fix false positives in subagent zero-tool-call gate"`
