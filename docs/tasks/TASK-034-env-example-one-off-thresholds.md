# TASK-034 Document HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS in .env.example (FR-47e)

## Status

todo

## Requirements

**Binding:** FR-47e
**BDD mode:** BDD-EXEMPT (documentation-only, no observable application behavior)
**Depends on:** TASK-033
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a user configuring household spend, I want `.env.example` to list
`HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS` alongside the other `HOUSEHOLD_SPEND_*`
variables, so that I discover the per-category override without having to
read the requirements document or source code.

## Description

TASK-033 (FR-47e) added `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS` to `Config` and
the requirements doc's config table, but the addition to `.env.example` was
missed. This task adds the missing entry, commented out like its sibling
`HOUSEHOLD_SPEND_*` variables, with a one-line comment giving the
`category:amount` example format.

## Branch

**Branch name:** `task/034-env-example-one-off-thresholds`
**Switch/create:** `git checkout -b task/034-env-example-one-off-thresholds`
**Make target:** `make branch-task f=TASK-034`

## Acceptance criteria

- [ ] 1. `.env.example` lists `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS` (commented
      out) directly after `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD`, with a comment
      giving the `category:amount` example format
- [ ] 2. `make lint` passes

## Out of scope

- Any change to `Config`, `household_spend.py`, or other application code
  (already shipped in TASK-033)

## Blockers

None

## Completion

**Date:** 2026-08-04
**Summary:** Added the missing `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS` line to
`.env.example`, commented out alongside its sibling `HOUSEHOLD_SPEND_*`
variables, with a comment showing the `category:amount` format — an omission
from TASK-033.
**Files changed:**

- `.env.example` - modified
- `docs/tasks/TASK-034-env-example-one-off-thresholds.md` - created

**Branch:** `git checkout task/034-env-example-one-off-thresholds`
**Stage:** `git add .env.example docs/tasks/TASK-034-env-example-one-off-thresholds.md`
**Commit:** `git commit -m "docs: add HOUSEHOLD_SPEND_ONE_OFF_THRESHOLDS to .env.example (TASK-034)"`
