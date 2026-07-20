# TASK-052 De-duplicate scoped-path lists in REQUIREMENTS_BUTLER_PULL.md

## Status
todo

## Requirements
**Binding:** Requirement 1, Requirement 3 (REQUIREMENTS_BUTLER_PULL.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-051 (must land first so this task starts from the corrected text)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of `REQUIREMENTS_BUTLER_PULL.md`, I want the set of
consumer-facing content paths (`templates/`, `claude-agents/`,
`claude-skills/`, ...) defined in exactly one place in the document, so that
adding a new content type in a future task can't silently leave the
"Acceptance criteria (overall)" section — or any other requirement's
prose — out of sync the way TASK-050 left Requirement 1 and "overall" out of
sync with `claude-skills/` (fixed in TASK-051).

## Description
`REQUIREMENTS_BUTLER_PULL.md` currently spells out the same list of scoped
paths in prose in at least three places: Requirement 1's description,
Requirement 3's description, and the "Acceptance criteria (overall)"
section. TASK-051 hand-synced all three for `claude-skills/`, but nothing
prevents the same drift from happening again the next time a content type is
added (e.g. a hypothetical `claude-commands/`).

This is a documentation-only refactor: introduce a single canonical
definition of "scoped paths" (e.g. a short list under Goals or a new
"Scoped paths" section near the top of the document) and rewrite
Requirement 1, Requirement 3, and the "overall" acceptance criteria to
reference it by name instead of re-enumerating the paths. No behavior
changes; this only reduces the document's own duplication.

This task does not touch `Makefile`, `scripts/`, or any test code — it is
scoped entirely to `REQUIREMENTS_BUTLER_PULL.md` wording. If tightening the
requirements text turns up an actual behavioral gap (e.g. a fourth
undocumented content type), stop and report it rather than folding a code
change into this task.

## Branch
**Branch name:** `task/052-requirements-butler-pull-single-source-scoped-paths`
**Switch/create:** `git checkout -b task/052-requirements-butler-pull-single-source-scoped-paths`
**Make target:** `make branch-task f=TASK-052`

## Acceptance criteria (Gherkin)
- [ ] Scenario: scoped paths defined once
      Given `REQUIREMENTS_BUTLER_PULL.md` after this task
      When a reader searches the document for the literal path
      `.butler/claude-skills/`
      Then it appears in exactly one canonical definition plus its
      Requirement-3-specific "Reproduced today" repro text, and every other
      mention is a reference to the canonical definition rather than a
      restated list
- [ ] Scenario: overall acceptance criteria stays complete without hand-sync
      Given the canonical scoped-paths definition lists `templates/`,
      `claude-agents/`, and `claude-skills/`
      When the "Acceptance criteria (overall)" section is read
      Then it derives its path coverage from that canonical definition
      (by reference or verbatim inclusion) rather than a separately
      maintained enumeration

## Out of scope
- Adding, removing, or changing which paths are scoped (still exactly
  `templates/`, `claude-agents/`, `claude-skills/` — content unchanged from
  TASK-051).
- Any change to `Makefile`, `scripts/`, or test code.
- TASK-039's broader repeat-pull/merge-conflict problem.

## Blockers
- None

## Completion
(left blank — filled in by Workflow Guardian on completion)
