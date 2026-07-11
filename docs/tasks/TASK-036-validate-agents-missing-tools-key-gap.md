# TASK-036 Close validate_agents.py gaps found during TASK-035 test review

## Status

done

## Description

The Test Design Reviewer's review of TASK-035's new characterization tests
(`tests/test_validate_agents.py`, `tests/test_hooks.py`) flagged two gaps in
`scripts/validate_agents.py` / `.claude/hooks/agent_result_gate.py` that were
deliberately left uncharacterized (characterization tests document existing
behavior as-is, they do not fix it):

1. **Missing `tools:` key is not flagged, only an empty one is.**
   `validate_file()` only requires `name` and `description` (`REQUIRED_KEYS`).
   If an `.agent.md` file has no `tools:` line at all, `validate_file()`
   reports zero errors — but `tools: []` (present and empty) is reported as
   `"'tools' is empty (agent will have no tools)"`. Since the entire point of
   this validator is to catch configurations that leave a subagent with no
   real tools (the TASK-025/TASK-034 root cause), an entirely absent `tools:`
   key produces the same "no tools" runtime outcome as an empty list, but
   currently passes validation silently. Decide whether `tools` should become
   a required key (fails validation if absent), and implement accordingly.
   See `tests/test_validate_agents.py::TestValidateFile::test_no_tools_key_at_all_is_not_reported_as_an_error`,
   which currently documents (not endorses) this gap.

2. **`agent_result_gate.py`'s "validator not found" fallback path is untested.**
   When `scripts/validate_agents.py` does not exist at
   `$CLAUDE_PROJECT_DIR/scripts/validate_agents.py`, the gate falls back to
   the literal string `"validator not found (scripts/validate_agents.py
   missing)"` instead of running the validator. This path exists in the code
   but has no test coverage. Add a test exercising it (e.g. a `project_dir`
   fixture with no `scripts/` directory at all) to `tests/test_hooks.py`,
   asserting the fallback string appears in the embedded validation result.

**Depends on:** TASK-035 (must land first; this task edits code TASK-035 introduces)

## Branch

**Branch name:** `task/036-validate-agents-missing-tools-key-gap`
**Switch/create:** `git checkout -b task/036-validate-agents-missing-tools-key-gap`
**Make target:** `make branch-task f=TASK-036`

## Acceptance criteria

- [x] Decision recorded (in this task's Completion summary) on whether `tools:` becomes a required key in `scripts/validate_agents.py`
- [x] If made required: a missing `tools:` key now produces a `validate_file()` error, and `tests/test_validate_agents.py::test_no_tools_key_at_all_is_not_reported_as_an_error` is updated to assert the new (fixed) behavior instead of documenting the gap
- [x] `tests/test_hooks.py` gains a test exercising `agent_result_gate.py`'s "validator not found" fallback string
- [x] `make validate-agents` still exits 0 against the real `.claude/agents/*.agent.md` files after any change
- [x] `make lint && make test` pass

## Completion

**Date:** 2026-07-09
**Summary:** Decision: `tools` was added to `REQUIRED_KEYS` in `scripts/validate_agents.py`, so a
missing `tools:` key now produces `"missing required key 'tools'"`, the same failure class as an
empty `tools: []` list -- both leave a subagent with no real tools at runtime, which is the exact
condition this validator exists to catch. Updated the README requirement text ("Agent
configuration validation" section) to document this before implementation, confirmed with the
user. Renamed `test_no_tools_key_at_all_is_not_reported_as_an_error` (which documented the gap) to
`test_missing_tools_key_is_reported` (asserts the fixed behavior), following TDD: the new
assertion was confirmed red against the old code, then green after the `REQUIRED_KEYS` change.
Added `test_validator_missing_uses_fallback_message` to `tests/test_hooks.py::TestAgentResultGateMain`,
exercising `agent_result_gate.py`'s previously-untested "validator not found" fallback path (a
`project_dir` fixture with no `scripts/` directory at all). Implemented via Implementation Worker
in an isolated worktree; its report was independently re-verified against ground truth (diff
content, commit hash `40f45d6b246d09db84564ed2c542fb4bb09a5fbf`, `pytest --collect-only` showing
98 tests) before the worktree was squash-merged. Post-merge on the task branch: `make test` shows
98 passed, 99% coverage (unchanged from the task-start baseline of 97 passed / 99%), `make lint`
and `make validate-agents` (9/9 valid) both pass. A separate, out-of-scope observation made during
this task -- `agent_result_gate.py` markers are project-global rather than session-scoped, so a
marker from an unrelated session can interrupt an in-progress task -- was split out into TASK-037
rather than fixed here.
**Files changed:**

- `scripts/validate_agents.py` — modified (`tools` added to `REQUIRED_KEYS`; docstring updated)
- `tests/test_validate_agents.py` — modified (renamed/updated test for the new required-key behavior)
- `tests/test_hooks.py` — modified (new fallback-path test)
- `CHANGELOG.md` — modified (Fixed entry, TASK-036)
- `README.md` — modified (documents `tools:` as a required key)
- `docs/tasks/TASK-036-validate-agents-missing-tools-key-gap.md` — modified (status, completion)
- `docs/tasks/TASK-037-stale-agent-failure-marker-staleness.md` — created (follow-up task, out of scope for TASK-036)

**Branch:** `git checkout task/036-validate-agents-missing-tools-key-gap`
**Stage:** `git add scripts/validate_agents.py tests/test_validate_agents.py tests/test_hooks.py CHANGELOG.md README.md docs/tasks/TASK-036-validate-agents-missing-tools-key-gap.md docs/tasks/TASK-037-stale-agent-failure-marker-staleness.md`
**Commit:** `git commit -m "Require tools: key in agent frontmatter validation and cover the validator-missing fallback"`
