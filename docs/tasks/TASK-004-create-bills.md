# TASK-004 Create bills in Firefly III (UC4)

## Status

todo

## Description

Implement `bills_creator.py` — the UC4 write layer. For each approved
`RecurringPattern` it performs the duplicate check per FR-05a–FR-05d
(spec 0.2.5) and creates a new bill via the Firefly III API if none exists.

**Duplicate criterion (spec Definitions, 0.2.5):** a duplicate bill is an
existing bill whose name equals the candidate bill name, compared
**case-sensitively after trimming leading and trailing whitespace**. Amount
and frequency are NOT part of the duplicate criterion — they only decide
which outcome a duplicate produces:

- Name match + identical amount range and `repeat_freq` → outcome
  `"already exists"` (FR-05b)
- Name match + differing amount range or `repeat_freq` → outcome
  `"exists with different parameters"`, with the differing values included
  in the report (FR-05c). No POST is made; the existing bill is never
  updated (SE-03)
- No local name match, but the POST is rejected by Firefly III with a
  name-uniqueness validation error (422, "name already in use") → outcome
  `"already exists"` (FR-05d). This is the safety net for case/collation
  differences between our case-sensitive check and the server's
  DB-collation-dependent uniqueness rule

**Prerequisite:** `create_bill()` must be added to `firefly-python-api` before this
task can be implemented. Open TASK-006 in that repo using the pattern from TASK-005
if it is missing. The method should POST to `POST /api/v1/bills` with name,
amount_min, amount_max, date, repeat_freq, and active fields, and must expose
the 422 validation payload to the caller so FR-05d can distinguish a
name-uniqueness rejection from other API errors.

Amount min/max is derived from `amount_mean` with a `±config.amount_margin`
fraction (FR-06). `repeat_freq` maps from the `frequency` string
(`monthly` → `monthly`, `quarterly` → `quarterly`, `half-yearly` → `half-year`,
`yearly` → `yearly`, `irregular` → not created unless explicitly approved).

Covers UC4, FR-05a, FR-05b, FR-05c, FR-05d, FR-06, FR-07b, FR-09.

## Branch

**Branch name:** `task/004-create-bills`
**Switch/create:** `git checkout -b task/004-create-bills`
**Make target:** `make branch-task f=TASK-004`

## Acceptance criteria

- [ ] `src/firefly_bills_analyzer/bills_creator.py` exposes
      `BillOutcome` (dataclass with fields `name: str`,
      `status: str` — one of `"created"`, `"exists"`, `"exists-diff"`,
      `"skipped"`, `"error"` — and `message: str`). `"exists"` maps to the
      spec outcome "already exists"; `"exists-diff"` maps to
      "exists with different parameters" and its `message` lists the
      differing values (candidate vs existing amount_min/amount_max/repeat_freq)
- [ ] `create_bills(patterns, client, config, dry_run) -> list[BillOutcome]`
      iterates over approved patterns and returns one `BillOutcome` per entry
- [ ] Amount min/max = `mean × (1 ∓ config.amount_margin)`, rounded to 2 decimals,
      computed before the duplicate check so the candidate's amounts are available
      for the FR-05b/FR-05c comparison
- [ ] Existing bills are fetched once via `client.get_bills()`; the duplicate
      check compares names case-sensitively after trimming leading and
      trailing whitespace on both sides (FR-05a). Amount and frequency are
      not part of the match
- [ ] A duplicate whose `amount_min`, `amount_max` (compared against the
      candidate's rounded values), and `repeat_freq` all equal the
      candidate's sets status `"exists"` without a POST call (FR-05b)
- [ ] A duplicate where any of `amount_min`, `amount_max`, or `repeat_freq`
      differs sets status `"exists-diff"` without a POST call, and the
      message includes each differing field with both values (FR-05c)
- [ ] A POST rejected by Firefly III with a name-uniqueness validation error
      (422) sets status `"exists"`, not `"error"` (FR-05d); other API errors
      set status `"error"` with the cause in the message (NFR-04 applies at
      the CLI layer)
- [ ] In dry-run mode all outcomes are `"skipped"` and no POST is made (FR-07b)
- [ ] `irregular` patterns produce status `"skipped"` with an explanatory message
      unless the caller explicitly passes `force=True`
- [ ] All API calls are logged at DEBUG level (FR-09)
- [ ] `tests/test_bills_creator.py` mocks `FireflyClient` and covers: happy-path
      creation; exact duplicate (name+amounts+frequency match → `"exists"`, no
      POST); name-only duplicate with differing amounts or frequency
      (→ `"exists-diff"`, no POST, differing values in message); name differing
      only in case or surrounding whitespace vs trimming (trim → match;
      case difference → no local match, POST attempted, mocked 422
      name-uniqueness → `"exists"` per FR-05d); dry-run mode; irregular skip;
      and a non-name-uniqueness API error (→ `"error"`)
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/bills_creator.py` — created
- `tests/test_bills_creator.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-004-create-bills.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/004-create-bills`
**Stage:** `git add src/firefly_bills_analyzer/bills_creator.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-004-create-bills.md`
**Commit:** `git commit -m "Add bills_creator.py for UC4 bill creation with FR-05a-d duplicate handling (TASK-004)"`
