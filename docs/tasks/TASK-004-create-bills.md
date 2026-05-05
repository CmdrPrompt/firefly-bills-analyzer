# TASK-004 Create bills in Firefly III (UC4)

## Status

todo

## Description

Implement `bills_creator.py` — the UC4 write layer. For each approved
`RecurringPattern` it checks for an existing bill with the same name (FR-05),
and creates a new one via the Firefly III API if none exists.

**Prerequisite:** `create_bill()` must be added to `firefly-python-api` before this
task can be implemented. Open TASK-006 in that repo using the pattern from TASK-005
if it is missing. The method should POST to `POST /api/v1/bills` with name,
amount_min, amount_max, date, repeat_freq, and active fields.

Amount min/max is derived from `amount_mean` with a `±config.amount_margin`
fraction (FR-06). `repeat_freq` maps from the `frequency` string
(`monthly` → `monthly`, `quarterly` → `quarterly`, `half-yearly` → `half-year`,
`yearly` → `yearly`, `irregular` → not created unless explicitly approved).

Covers UC4, FR-05, FR-06, FR-09.

## Branch

**Branch name:** `task/004-create-bills`
**Switch/create:** `git checkout -b task/004-create-bills`
**Make target:** `make branch-task f=TASK-004`

## Acceptance criteria

- [ ] `src/firefly_bills_analyzer/bills_creator.py` exposes
      `BillOutcome` (dataclass with fields `name: str`,
      `status: str` — one of `"created"`, `"exists"`, `"skipped"`, `"error"`,
      and `message: str`)
- [ ] `create_bills(patterns, client, config, dry_run) -> list[BillOutcome]`
      iterates over approved patterns and returns one `BillOutcome` per entry
- [ ] Existing bills are fetched once via `client.get_bills()` and matched by name
      (case-insensitive); a match sets status `"exists"` without an API call
- [ ] In dry-run mode all outcomes are `"skipped"` and no POST is made (FR-07)
- [ ] Amount min/max = `mean × (1 ∓ config.amount_margin)`, rounded to 2 decimals
- [ ] `irregular` patterns produce status `"skipped"` with an explanatory message
      unless the caller explicitly passes `force=True`
- [ ] All API calls are logged at DEBUG level (FR-09)
- [ ] `tests/test_bills_creator.py` mocks `FireflyClient` and covers: happy-path
      creation, duplicate detection, dry-run mode, irregular skip, and API error
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/bills_creator.py` — created
- `tests/test_bills_creator.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-004-create-bills.md` — modified

**Branch:** `git checkout task/004-create-bills`
**Stage:** `git add src/firefly_bills_analyzer/bills_creator.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-004-create-bills.md`
**Commit:** `git commit -m "Add bills_creator.py for UC4 bill creation with duplicate detection (TASK-004)"`
