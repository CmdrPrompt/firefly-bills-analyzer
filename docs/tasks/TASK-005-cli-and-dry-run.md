# TASK-005 CLI orchestration, review flow, and dry-run (UC3 + UC5)

## Status

todo

## Description

Wire all previous modules together into a working CLI. The entry-point in
`__main__.py` is extended to run the full pipeline: load config → fetch
transactions (UC1) → filter by category (UC6, TASK-006) → identify patterns
(UC2) → interactive review (UC3) → create bills (UC4) — or skip creation in
dry-run mode (UC5).

Also adds `exporter.py` for CSV/JSON export (FR-08, UC5).

**Depends on:** TASK-002, TASK-003, TASK-004 (pipeline stages being wired),
TASK-006 (category filtering step), TASK-008 (category-aware bill naming),
and TASK-007 (`--clear-cache` wiring in `__main__.py`), *if* TASK-007 is
built — see its Open Item #8 note; it may be deprioritized for the
terminal-only MVP. If TASK-007 is skipped, drop the `cache.clear_all()` call
from `--clear-cache` and leave it a no-op with a "caching not implemented"
message instead. Implement this task last so the full pipeline — including
filtering and (if present) cache clearing — is assembled in one place instead
of being retrofitted afterwards.

Covers UC3 (terminal flow), UC5, FR-07a, FR-07b, FR-08.

## Branch

**Branch name:** `task/005-cli-and-dry-run`
**Switch/create:** `git checkout -b task/005-cli-and-dry-run`
**Make target:** `make branch-task f=TASK-005`

## Acceptance criteria

- [ ] `python -m firefly_bills_analyzer` runs the full pipeline end-to-end,
      including `category_filter.filter_transactions` between fetch and
      analyze (errors before creating any bills are surfaced as plain
      messages, not stack traces — NFR-04)
- [ ] Without `--auto-approve`, each suggestion above `config.high_confidence_threshold`
      is printed and the user is prompted `[y]es / [n]o / [a]ll / [q]uit`
- [ ] Entries below the threshold are listed but defaulted to `n`; the user can
      still approve them interactively
- [ ] `--auto-approve` approves all entries at or above
      `config.high_confidence_threshold` without prompting
- [ ] `--dry-run` prints suggestions and passes `dry_run=True` to `create_bills`;
      no bills are created; output is also exported if `EXPORT_FORMAT` is set
- [ ] `src/firefly_bills_analyzer/exporter.py` exposes
      `export(patterns, fmt, path)` where `fmt` is `"csv"`, `"json"`, or `"none"`;
      when `fmt` is `"none"` the function is a no-op
- [ ] `EXPORT_FORMAT` env var controls default export format; export path defaults
      to `./firefly-bills-{timestamp}.{ext}`
- [ ] `tests/test_exporter.py` covers CSV output, JSON output, and the no-op path
      using Hypothesis for the data transformation
- [ ] `tests/test_main.py` mocks fetcher, analyzer, and bills_creator and verifies
      the `--dry-run` and `--auto-approve` flag behaviours without touching
      the network
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/__main__.py` — modified
- `src/firefly_bills_analyzer/exporter.py` — created
- `tests/test_exporter.py` — created
- `tests/test_main.py` — created
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-005-cli-and-dry-run.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/005-cli-and-dry-run`
**Stage:** `git add src/firefly_bills_analyzer/__main__.py src/firefly_bills_analyzer/exporter.py tests/test_exporter.py tests/test_main.py CHANGELOG.md docs/tasks/TASK-005-cli-and-dry-run.md`
**Commit:** `git commit -m "Wire CLI pipeline with interactive review, dry-run, and CSV/JSON export (TASK-005)"`
