# TASK-035 Fix agent tools frontmatter and add validation plus subagent hard gate

## Status

done

## Description

All nine agent definitions in `.claude/agents/*.agent.md` (and their sources in
`claude-agents/`) declare invalid tool names in their `tools:` frontmatter
(`read, search, edit, write, execute, todo, agent`). These are not Claude Code
tool names. Claude Code drops unknown names silently, so every subagent was
spawned with an empty tool set. A model without tools cannot emit `tool_use`
blocks; instead it narrates tool-call-shaped text (`read {"path": ...}`) and
ends its turn with zero tool uses. Coordinator follow-up messages cannot fix
this, since the cause is the request configuration, not the model's behavior.

Observed in three subagent types across TASK-025 and TASK-034 (Implementation
Worker, Test Writer, PR Reviewer). Diagnosed 2026-07-09 from the raw agent
transcripts: `end_turn` with ~70 output tokens, zero `tool_use` blocks, and
system-prompt cache sizes (~4-6k tokens) too small to contain tool schemas.

Three-part remediation:

1. **Fix**: replace the invalid names with real Claude Code tool names
   (`Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `TodoWrite`, `Task`) in
   all nine agent files, in both `.claude/agents/` and `claude-agents/`, and
   update the prose in the Tool usage sections to match.
2. **Static prevention**: add `scripts/validate_agents.py` (stdlib-only) and a
   `make validate-agents` target that validates frontmatter (required keys,
   non-empty `tools:` list, only whitelisted tool names, `mcp__server__tool`
   allowed by pattern, did-you-mean hints for case errors). Wire into
   pre-commit and CI so a broken definition cannot reach `main`.
3. **Runtime hard gate**: register two hooks in `.claude/settings.json`.
   `.claude/hooks/subagent_toolcheck.py` (SubagentStop) detects a subagent
   turn ending with zero `tool_use` blocks and writes a marker to
   `.claude/state/agent-failures/`. `.claude/hooks/agent_result_gate.py`
   (PostToolUse on `Agent|Task`) consumes the marker in the coordinator's
   session, runs the validator, and exits 2 so the coordinator receives a
   deterministic directive: treat as configuration error, do not retry or
   respawn, report to the user until `make validate-agents` passes.

Also updates README (What's included, new "Agent configuration validation"
section, and corrects the agent overview from seven to the actual nine agents)
and CHANGELOG (Fixed + Added entries under Unreleased).

**Depends on:** none

## Branch

**Branch name:** `task/035-agent-tools-validation-gate`
**Switch/create:** `git checkout -b task/035-agent-tools-validation-gate`
**Make target:** `make branch-task f=TASK-035`

## Acceptance criteria

- [x] All nine `.claude/agents/*.agent.md` files declare only valid Claude Code tool names in `tools:` frontmatter, and `claude-agents/` sources are kept in sync (`make check-agents-sync` passes)
- [x] Prose references to tool names in agent bodies (Tool usage sections, workflow-guardian's `edit` mention) use the real names
- [x] `make validate-agents` exists, exits 0 on the fixed definitions, and exits 1 with per-file, per-tool errors on the pre-fix definitions
- [x] `validate-agents` runs in pre-commit (triggered by changes under `.claude/agents/`) and as a CI step
- [x] `.claude/settings.json` registers the SubagentStop and PostToolUse hooks with `$CLAUDE_PROJECT_DIR`-relative paths
- [x] `subagent_toolcheck.py` writes a marker for a transcript with zero tool calls and at least one assistant turn, and does NOT trigger on a transcript containing a `tool_use` block (verified against the real TASK-034 failure transcripts)
- [x] `agent_result_gate.py` consumes markers exactly once, embeds the validator output, and exits 2; exits 0 silently when no markers exist
- [x] `.claude/state/` is gitignored
- [x] README documents the validation and the gate; agent table lists all nine agents
- [x] CHANGELOG has Fixed and Added entries under Unreleased
- [x] Live verification: spawn a subagent after the fix and confirm the first real turn ends with `stop_reason='tool_use'` in the agent transcript
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-09
**Summary:** Replaced the invalid `tools:` frontmatter (`read, search, edit, write, execute, todo,
agent`) in all nine `.claude/agents/*.agent.md` files (and their `claude-agents/` sources) with
real Claude Code tool names, and fixed a leftover lowercase prose reference in
`workflow-guardian.agent.md`. Added `scripts/validate_agents.py` (stdlib-only static validator,
wired into pre-commit and `.github/workflows/ci.yml`) and a runtime hard gate
(`.claude/hooks/subagent_toolcheck.py` + `.claude/hooks/agent_result_gate.py`, registered in
`.claude/settings.json`) that detects a subagent finishing with zero tool calls and escalates it
to the coordinator as a blocking configuration error instead of allowing a retry. Verified
`subagent_toolcheck.py` against the two real TASK-034 failure transcripts (both correctly produce
a marker) and against a synthetic transcript containing a `tool_use` block (correctly produces no
marker). Live-verified the fix itself: the Characterization Test Writer and Test Design Reviewer
subagents spawned during this task's own verification both completed with real tool calls
(`stop_reason='tool_use'` on their first real turn, confirmed in their transcripts) — a direct,
practical demonstration that the frontmatter fix resolves the narrated-tool-call failure mode.
Added characterization tests for the three new Python scripts (`tests/test_validate_agents.py`,
19 tests; `tests/test_hooks.py`, 13 tests after a Test Design Reviewer pass — see below) via the
Characterization Test Writer agent, run in a worktree whose branch had no commits yet (this task's
work was still uncommitted at the time); the agent correctly detected this, read the real files by
absolute path from the main working tree, and copied them into its worktree rather than
reconstructing them from the task description. Test Design Reviewer scored the result 7.7/10
(Good) and flagged three fixable issues (addressed before staging, per this project's TASK-028
rule that real findings must be resolved before `stage-current-task`): a real, unmocked
`subprocess.run` call in two gate tests (now stubbed), one overly bundled multi-assertion test
(split into a structural marker-fields comparison plus a separate consumption test), and two
CLI-output assertions coupled to exact literal wording (loosened to independent substring checks).
Also flagged two out-of-scope gaps in the reviewed code, split out into TASK-036: `validate_file()`
does not flag an entirely absent `tools:` key (only an empty list), and the "validator not found"
fallback string in `agent_result_gate.py` has no test coverage.
**Files changed:**

- `.claude/agents/*.agent.md` — modified (nine files, fixed tools frontmatter)
- `claude-agents/*.agent.md` — modified (synced sources)
- `scripts/validate_agents.py` — created
- `.claude/hooks/subagent_toolcheck.py` — created
- `.claude/hooks/agent_result_gate.py` — created
- `.claude/settings.json` — created
- `.github/workflows/ci.yml` — created
- `Makefile` — modified (validate-agents target, .PHONY, help)
- `.pre-commit-config.yaml` — modified (validate-agents hook)
- `.gitignore` — modified (.claude/state/)
- `README.md` — modified
- `CHANGELOG.md` — modified
- `tests/test_validate_agents.py` — created
- `tests/test_hooks.py` — created
- `docs/tasks/TASK-035-agent-tools-validation-gate.md` — created

**Branch:** `git checkout task/035-agent-tools-validation-gate`
**Stage:** `git add .claude/ claude-agents/ scripts/ .github/ Makefile .pre-commit-config.yaml .gitignore README.md CHANGELOG.md tests/test_validate_agents.py tests/test_hooks.py docs/tasks/TASK-035-agent-tools-validation-gate.md`
**Commit:** `git commit -m "Fix agent tools frontmatter, add validation and subagent hard gate"`
