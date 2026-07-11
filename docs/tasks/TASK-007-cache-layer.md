# TASK-007 Local file cache layer (UC7)

## Status

done

**2026-07-11:** Un-deferred per further resolution of Open Item #8 (spec
v0.2.16). New motivation, independent of the web UI: repeated local
development/test runs against a real Firefly III instance re-fetch the same
paginated transaction history every time; a TTL-aware disk cache removes
that cost for repeated `--dry-run` runs during development. Scope is
unchanged from the original description below — transactions and bills
caching only; categories/payees caching and the web UI's "Clear cache"
button remain deferred, contingent on Open Item #5.

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
which this task makes cache-aware. TASK-005 (CLI wiring) already shipped
without this task; `--clear-cache` upgrades from its current no-op to
actually deleting cache files once this task lands.

Covers UC7, FR-21, FR-22, FR-23, FR-25, NFR-09.

## Branch

**Branch name:** `task/007-cache-layer`
**Switch/create:** `git checkout -b task/007-cache-layer`
**Make target:** `make branch-task f=TASK-007`

## Acceptance criteria

- [x] `src/firefly_bills_analyzer/cache.py` exposes
      `read(name: str, ttl_seconds: int, cache_dir: Path) -> Any | None`,
      returning `None` when the file is missing or its stored timestamp is
      older than `ttl_seconds`
- [x] `cache.py` exposes `write(name: str, data: Any, cache_dir: Path) -> None`,
      writing `data` plus a timestamp to `<cache_dir>/<name>.json`
- [x] `cache.py` exposes `invalidate(name: str, cache_dir: Path) -> None` and
      `clear_all(cache_dir: Path) -> None`
- [x] `cache_dir` is `config.cache_dir` at every call site (`fetcher.py`,
      `bills_creator.py`, `__main__.py`) and is created on write if it does
      not exist; existing files are left untouched across restarts (NFR-09).
      Deviation from the original description: `cache.py`'s own functions
      require `cache_dir` explicitly rather than defaulting to
      `config.cache_dir` internally, keeping the generic module decoupled
      from `Config` — callers pass `Path(config.cache_dir)` instead
- [x] `fetcher.fetch_transactions` reads from the transactions cache when
      fresh (`CACHE_TTL_TRANSACTIONS`) and writes to it after a live fetch.
      The cached entry also stores the `start`/`end` window and is ignored
      (treated as a miss) if the configured lookback window no longer
      matches, so changing `LOOKBACK_MONTHS` can't silently serve
      wrong-range data
- [x] `bills_creator.create_bills` reads the bills list from cache when fresh
      (`CACHE_TTL_BILLS`) instead of always calling `client.get_bills()`, and
      calls `cache.invalidate("bills", ...)` synchronously right after any
      successful bill creation, before returning that entry's `BillOutcome`
      (FR-23)
- [x] `__main__.py`'s `--clear-cache` flag calls `cache.clear_all()` on
      startup, before any fetch (FR-25)
- [x] `tests/test_cache.py` covers: fresh read, stale/expired read returning
      `None`, exact-TTL-boundary read still fresh, missing-file read
      returning `None`, corrupt-file read returning `None`, write-then-read
      round trip, invalidate, and clear_all
- [x] `tests/test_fetcher.py` and `tests/test_bills_creator.py` gain cases for
      the cache-hit path (no API call made), cache-miss path, stale-cache
      path, exact-TTL-boundary path, and (fetcher-specific) window-mismatch
      path
- [x] `make lint && make test` pass with coverage >= baseline

## Completion

**Date:** 2026-07-11
**Summary:** Added `cache.py`, a generic TTL-aware JSON file cache
(`read`/`write`/`invalidate`/`clear_all`) with no dependency on `Config`.
Wired it into `fetcher.fetch_transactions` (transactions cache, keyed with
the lookback window's start/end dates to avoid serving stale-window data)
and `bills_creator.create_bills` (bills cache via a new `_get_bills_cached()`
helper, invalidated synchronously right after a successful `create_bill()`
call, per FR-23). `__main__.py`'s `--clear-cache` flag now actually deletes
cache files instead of printing a no-op message. Verified against the real
Firefly III instance: first run (cache miss) took ~2 minutes to fetch 45
pages; second run (cache hit) took ~0.4 seconds — the development-velocity
motivation behind un-deferring this task. Test Design Reviewer scored the
task's test suite 9.1/10 on Farley's 8 properties; its two minor findings
were fixed: a byte-identical duplicate test in `TestCategoryAwareNaming`
was merged into one (with its intent folded into a comment), and an
exact-TTL-boundary test was added for the bills cache specifically at the
`create_bills()` call site (previously only covered generically in
`test_cache.py`).
**Files changed:**

- `src/firefly_bills_analyzer/cache.py` — created
- `src/firefly_bills_analyzer/fetcher.py` — modified (cache-aware fetch,
  window-keyed)
- `src/firefly_bills_analyzer/bills_creator.py` — modified (`_get_bills_cached()`
  helper, cache-aware bills read + invalidation)
- `src/firefly_bills_analyzer/__main__.py` — modified (`--clear-cache` wiring)
- `tests/test_cache.py` — created
- `tests/test_fetcher.py` — modified (`tmp_path`-isolated `cache_dir` for all
  tests; new cache-hit/miss/stale/window-mismatch tests)
- `tests/test_bills_creator.py` — modified (`tmp_path`-isolated `cache_dir`
  for all tests; new `TestBillsCache` class; merged a pre-existing duplicate
  test)
- `tests/test_main.py` — modified (`TestClearCache` now verifies actual
  cache-clearing instead of the old no-op message)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-007-cache-layer.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/007-cache-layer`
**Stage:** `git add src/firefly_bills_analyzer/cache.py src/firefly_bills_analyzer/fetcher.py src/firefly_bills_analyzer/bills_creator.py src/firefly_bills_analyzer/__main__.py tests/test_cache.py tests/test_fetcher.py tests/test_bills_creator.py tests/test_main.py CHANGELOG.md docs/tasks/TASK-007-cache-layer.md docs/tasks/README.md`
**Commit:** `git commit -m "Add TTL-aware disk cache for transactions and bills (TASK-007)"`

**Branch:** `git checkout task/007-cache-layer`
**Stage:** `git add src/firefly_bills_analyzer/cache.py src/firefly_bills_analyzer/fetcher.py src/firefly_bills_analyzer/bills_creator.py src/firefly_bills_analyzer/__main__.py tests/test_cache.py tests/test_fetcher.py tests/test_bills_creator.py CHANGELOG.md docs/tasks/TASK-007-cache-layer.md`
**Commit:** `git commit -m "Add cache.py for UC7 TTL-based file caching of transactions and bills (TASK-007)"`
