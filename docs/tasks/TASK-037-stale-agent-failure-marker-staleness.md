# TASK-037 Ignore stale subagent-failure markers in agent_result_gate

## Status

done

## Description

`.claude/state/agent-failures/` is project-global state, not scoped to a single
Claude Code session: `subagent_toolcheck.py` (SubagentStop) can write a marker
in one terminal/session, and `agent_result_gate.py` (PostToolUse on
`Agent|Task`) consumes (reports + deletes) whatever markers it finds on the
*next* subagent call in *any* session for the project — including one working
on a completely unrelated task.

Observed 2026-07-09: while running TASK-036 in one session, a marker for a
`PR Reviewer` agent that this session never spawned tripped the hard gate,
interrupting unrelated work. The marker was real (a genuine zero-tool-call
failure from another session) but stale by the time it surfaced here, and its
sudden appearance was confusing without any age context.

Each marker already carries a `detected_at` UTC timestamp
(`subagent_toolcheck.py`, ISO-8601 via `time.strftime("%Y-%m-%dT%H:%M:%SZ",
time.gmtime())`), but `agent_result_gate.py` does not currently read it —
every marker found is reported as an active gate trip regardless of age.

Fix: `agent_result_gate.py` should treat markers older than a staleness
threshold as informational rather than an active blocking trip:

- Markers are still always consumed (deleted) on read, exactly as today —
  this is not a retention/audit feature.
- Markers newer than the threshold are reported and escalated exactly as
  today: printed to stderr, contribute to a non-zero exit code.
- Markers at or older than the threshold are **not** included in the
  escalation message and do **not** contribute to a non-zero exit code. If
  *all* found markers are stale, the hook exits 0 silently (matching the
  existing "no markers" behavior) rather than tripping the gate for
  something no longer actionable in the current session.
- Threshold: 60 minutes, hardcoded as a module-level constant (no new config
  surface — this project already avoids adding config for internal tooling
  unless there's a proven need).
- A marker with a missing or unparseable `detected_at` field is treated as
  fresh (fail toward reporting, not toward silent dropping), since that is
  the safer default for a failure-detection gate.

Explicitly rejected alternative (raised during TASK-036 review): tying marker
cleanup to PR merge. Rejected because marker lifecycle (a runtime hook
failure) is orthogonal to git PR lifecycle — a marker can exist without any
PR ever being opened for the task that triggered it, and this would leave the
cross-session-surprise problem unsolved for any work that isn't wrapped in a
PR.

**Depends on:** none (independent of TASK-036, though discovered during it)

## Branch

**Branch name:** `task/037-stale-agent-failure-marker-staleness`
**Switch/create:** `git checkout -b task/037-stale-agent-failure-marker-staleness`
**Make target:** `make branch-task f=TASK-037`

## Acceptance criteria

- [x] `agent_result_gate.py` reads each marker's `detected_at` and classifies it as stale (>= 60 min old) or fresh
- [x] Fresh markers are reported/escalated exactly as before (stderr message, exit 2)
- [x] Stale markers are deleted (consumed) but excluded from the stderr message and do not force exit 2
- [x] If all found markers are stale, the hook exits 0 with no stderr output
- [x] A marker with missing/unparseable `detected_at` is treated as fresh
- [x] `tests/test_hooks.py` gains characterization/behavior tests for: all-stale (exit 0, silent), mixed stale+fresh (only fresh reported, stale still deleted), and missing/unparseable `detected_at` (treated as fresh)
- [x] README's "Agent configuration validation" section documents the staleness behavior
- [x] CHANGELOG.md has a behavior-first entry under Unreleased (TASK-037 suffix)
- [x] `make lint && make test` pass
## Completion

**Date:** 2026-07-09
**Summary:** Implemented staleness filtering for subagent failure markers. Markers older than 60 minutes are no longer reported as gate trips, preventing cross-session surprises. Markers are still consumed (deleted) on read. Added 5 new test cases covering all-stale, mixed stale/fresh, and invalid timestamp scenarios. Updated README and CHANGELOG.md. All 103 tests pass with 99% coverage baseline maintained.
**Files changed:**
- `.claude/hooks/agent_result_gate.py` — added staleness threshold constant and `is_marker_stale()` function to classify markers; modified `main()` to separate fresh from stale and only escalate fresh failures
- `tests/test_hooks.py` — added helper `_write_marker_with_timestamp()` and 5 new test cases in `TestAgentResultGateStaleness` class
- `README.md` — added "Stale marker handling" section to "Agent configuration validation"
- `CHANGELOG.md` — added behavior-first entry under Fixed section
**Branch:** `git checkout task/037-stale-agent-failure-marker-staleness`
**Stage:** `git add .claude/hooks/agent_result_gate.py tests/test_hooks.py README.md CHANGELOG.md`
**Commit:** `git commit -m "Fix: subagent failure markers older than 60 minutes no longer trip hard gate (TASK-037)"`
