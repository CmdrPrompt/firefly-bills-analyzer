# TASK-052 De-duplicate scoped-path lists in REQUIREMENTS_BUTLER_PULL.md

## Status
done

## Requirements
**Binding:** Requirement 1, Requirement 3, Requirement 4 (REQUIREMENTS_BUTLER_PULL.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-051, TASK-053 (both must land first so this task starts
from the fully corrected text — Requirement 4, added by TASK-053, repeats the
same scoped-path enumeration and would otherwise need a second hand-sync pass)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of `REQUIREMENTS_BUTLER_PULL.md`, I want the set of
consumer-facing content paths (`templates/`, `claude-agents/`,
`claude-skills/`, ...) defined in exactly one place in the document, so that
adding a new content type or a new requirement in a future task can't
silently leave the "Acceptance criteria (overall)" section — or any other
requirement's prose — out of sync the way TASK-050 left Requirement 1 and
"overall" out of sync with `claude-skills/` (fixed in TASK-051), and the way
TASK-053's Requirement 4 repeated the same three-path list a third time
rather than referencing a shared definition.

## Description
`REQUIREMENTS_BUTLER_PULL.md` currently spells out the same list of scoped
paths in prose in at least four places: Requirement 1's description,
Requirement 3's description, Requirement 4's description (guard condition,
bypass note, and use case), and the "Acceptance criteria (overall)" section.
TASK-051 hand-synced Requirement 1/3/overall for `claude-skills/`, and
TASK-053 hand-wrote a fourth copy for Requirement 4 rather than referencing
the existing ones. Nothing prevents the same drift from happening again the
next time a content type or a requirement referencing the scoped paths is
added (e.g. a hypothetical `claude-commands/`, or a Requirement 5).

This is a documentation-only refactor: introduce a single canonical
definition of "scoped paths" (e.g. a short list under Goals or a new
"Scoped paths" section near the top of the document) and rewrite
Requirement 1, Requirement 3, Requirement 4, and the "overall" acceptance
criteria to reference it by name instead of re-enumerating the paths. Each
requirement's own "Reproduced today" repro text and use-case transcript may
still name the specific path(s) relevant to that repro — those are
illustrative, not the canonical definition, and are out of scope for
de-duplication. No behavior changes; this only reduces the document's own
duplication.

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
- [x] Scenario: scoped paths defined once
      Given `REQUIREMENTS_BUTLER_PULL.md` after this task
      When a reader searches the document for the literal path
      `.butler/claude-skills/`
      Then it appears in exactly one canonical definition plus each
      requirement's own "Reproduced today"/use-case repro text (Requirement
      3 and Requirement 4 each keep their own illustrative mention), and
      every other mention — including Requirement 1, Requirement 3's and
      Requirement 4's change-detection/guard descriptions, and "overall" —
      is a reference to the canonical definition rather than a restated list
- [x] Scenario: overall acceptance criteria stays complete without hand-sync
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
**Date:** 2026-07-20
**Summary:** Added a single "Scoped paths" section to `REQUIREMENTS_BUTLER_PULL.md`
(after Non-goals, before Requirement 1) naming the three consumer-facing
content paths (`templates/`, `claude-agents/`, `claude-skills/`) once, and
rewrote Requirement 1's description, Requirement 3's change-detection bullet,
Requirement 4's description/guard bullets, and four bullets under "Acceptance
criteria (overall)" to reference "the scoped paths (see 'Scoped paths'
above)" instead of re-enumerating the list. Requirement 1's description
previously only named 2 of the 3 paths (missing `claude-skills/`) while
"overall" already required all 3 — referencing the canonical 3-path list from
Requirement 1 resolves that inconsistency without changing the required
behavior (Requirement 1 + Requirement 3 combined already required diffing all
3 paths). Each requirement's own "Reproduced today"/"Use case" illustrative
text, and the single `generate-governance-files` SKILL.md-copy bullet, were
left untouched per the task's explicit scope. Docs-only change; no `Makefile`,
`scripts/`, or test code touched.
**Files changed:**
- `REQUIREMENTS_BUTLER_PULL.md` - modified
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md` - modified
**Branch:** `git checkout task/052-requirements-butler-pull-single-source-scoped-paths`
**Stage:** `git add REQUIREMENTS_BUTLER_PULL.md CHANGELOG.md docs/tasks/TASK-052-requirements-butler-pull-single-source-scoped-paths.md`
**Commit:** `git commit -m "Consolidate scoped-path list in REQUIREMENTS_BUTLER_PULL.md into one canonical definition"`
