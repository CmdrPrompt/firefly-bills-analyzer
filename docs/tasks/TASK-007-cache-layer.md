# TASK-007 Local file cache layer (UC7)

## Status

todo

## Description

Implement `cache.py` — the UC7 cache layer named in the Architecture section of
the spec but not yet covered by any task. It provides a generic, TTL-aware
JSON file cache that other modules read/write through, and persists across
restarts (NFR-09).

Scope for this task is the generic cache module plus its two CLI-relevant
consumers:

- `fetcher.py` (TASK-002): reads/writes the transactions cache
  (`CACHE_TTL_TRANSACTIONS`)
- `bills_creator.py` (TASK-004): reads/writes the bills cache
  (`CACHE_TTL_BILLS`) and invalidates it synchronously after creating a bill
  (FR-23)

Categories and payees caching (FR-21's remaining two data sets) are consumed
only via the `/api/categories` web endpoint, which does not exist yet in the
terminal-only MVP. `cache.py` itself must still support all four named data
sets generically (FR-21, FR-22) so the web layer can reuse it without changes
when it is built; only the two web-only consumers are deferred.

`--clear-cache` (already parsed in `__main__.py` per TASK-001) currently has
no effect — this task makes the flag functional by deleting cache files
during startup (FR-25).

**Depends on:** TASK-002 (`fetcher.py`) and TASK-004 (`bills_creator.py`),
which this task makes cache-aware. Implement after TASK-008 and before
TASK-005, so the final CLI wiring (TASK-005) assembles a pipeline where
fetch, filter, analyze, create, and cache-clear are all already in place.

**⚠ Open Item #8 (spec):** FR-21/22/23/NFR-09 are written as hard "shall"
requirements, but the caching mechanism was originally motivated by the web
UI's repeated polling (UC7's `/api/categories` and `/api/analyze` endpoints),
not a one-shot CLI run. If the web UI ends up deferred or dropped (Open Item
#5), confirm with the user whether this task is still worth building before
TASK-005, or whether it should be deprioritized/skipped for the terminal-only
MVP. Do not assume caching is mandatory here just because the spec says
"shall" — that obligation level itself hasn't been individually confirmed.

Covers UC7, FR-21, FR-22, FR-23, FR-25, NFR-09.

## Branch

**Branch name:** `task/007-cache-layer`
**Switch/create:** `git checkout -b task/007-cache-layer`
**Make target:** `make branch-task f=TASK-007`

## Acceptance criteria

- [ ] `src/firefly_bills_analyzer/cache.py` exposes
      `read(name: str, ttl_seconds: int, cache_dir: Path) -> Any | None`,
      returning `None` when the file is missing or its stored timestamp is
      older than `ttl_seconds`
- [ ] `cache.py` exposes `write(name: str, data: Any, cache_dir: Path) -> None`,
      writing `data` plus a timestamp to `<cache_dir>/<name>.json`
- [ ] `cache.py` exposes `invalidate(name: str, cache_dir: Path) -> None` and
      `clear_all(cache_dir: Path) -> None`
- [ ] `cache_dir` defaults to `config.cache_dir` and is created if it does not
      exist; existing files are left untouched across restarts (NFR-09)
- [ ] `fetcher.fetch_transactions` reads from the transactions cache when
      fresh (`CACHE_TTL_TRANSACTIONS`) and writes to it after a live fetch
- [ ] `bills_creator.create_bills` reads the bills list from cache when fresh
      (`CACHE_TTL_BILLS`) instead of always calling `client.get_bills()`, and
      calls `cache.invalidate("bills", ...)` synchronously right after any
      successful bill creation, before returning that entry's `BillOutcome`
      (FR-23)
- [ ] `__main__.py`'s `--clear-cache` flag calls `cache.clear_all()` on
      startup, before any fetch (FR-25)
- [ ] `tests/test_cache.py` covers: fresh read, stale/expired read returning
      `None`, missing-file read returning `None`, write-then-read round trip,
      invalidate, and clear_all
- [ ] `tests/test_fetcher.py` and `tests/test_bills_creator.py` gain cases for
      the cache-hit path (no API call made) and cache-miss path
- [ ] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/firefly_bills_analyzer/cache.py` — created
- `src/firefly_bills_analyzer/fetcher.py` — modified (cache-aware fetch)
- `src/firefly_bills_analyzer/bills_creator.py` — modified (cache-aware bills read + invalidation)
- `src/firefly_bills_analyzer/__main__.py` — modified (`--clear-cache` wiring)
- `tests/test_cache.py` — created
- `tests/test_fetcher.py` — modified
- `tests/test_bills_creator.py` — modified
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-007-cache-layer.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/007-cache-layer`
**Stage:** `git add src/firefly_bills_analyzer/cache.py src/firefly_bills_analyzer/fetcher.py src/firefly_bills_analyzer/bills_creator.py src/firefly_bills_analyzer/__main__.py tests/test_cache.py tests/test_fetcher.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-007-cache-layer.md`
**Commit:** `git commit -m "Add cache.py for UC7 TTL-based file caching of transactions and bills (TASK-007)"`
