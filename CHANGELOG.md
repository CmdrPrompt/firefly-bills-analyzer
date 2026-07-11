# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Recurring-payment identification now splits a payee's transactions into
  separate patterns when they reveal genuinely parallel simultaneous charges
  billed through the same merchant or payee name (e.g. two subscriptions, or
  two household members billed the same fee) — detected by same-date
  co-occurrence of differing amounts, not amount variance alone, so a single
  bill whose amount fluctuates over time (e.g. a metered electricity bill
  priced by season and consumption) is never incorrectly fragmented. Each
  resulting cluster is scored independently, and its bill name is
  disambiguated with its representative amount when more than one cluster
  qualifies for the same payee. Same-date transactions within a cluster
  (e.g. the same fee billed once per household member) are now summed into
  a single billing event before frequency/interval are computed, so they no
  longer collapse the median interval to 0 and misclassify a clean monthly
  pattern as irregular. New `AMOUNT_CLUSTER_TOLERANCE` setting controls the
  amount-gap tolerance used when clustering. (TASK-012)

- Fetching transactions now shows a CLI progress bar (pages fetched out of
  the total), driven by `firefly-python-api`'s per-page `on_page` callback.
  (TASK-013)

- Recurring patterns now resolve and report the source account they are paid
  from (`analyzer.identify_recurring`): a single dominant account name, or a
  `(varies)` indicator when a payee's transactions span more than one source
  account. This is shown in CLI review/auto-approve suggestions and exported
  as `source_account_name`/`source_account_varies` columns in CSV/JSON export.
  (TASK-011)

- Python package `firefly_bills_analyzer` with `config.py` (loads all env vars with
  typed defaults, raises `ConfigError` for missing required values) and `__main__.py`
  (CLI entry-point with `--dry-run`, `--auto-approve`, `--clear-cache` flags). (TASK-001)
- `python-dotenv` added as runtime dependency for automatic `.env` loading. (TASK-001)
- `firefly-python-api` added as a git subtree under `lib/firefly-python-api/`. (TASK-001)
- Fetch withdrawal transactions from Firefly III for the configured lookback window
  (`fetcher.fetch_transactions`); connection failures exit with a human-readable
  message instead of a stack trace, and all API calls are logged at DEBUG level. (TASK-002)
- Filter transactions by category include/exclude lists and configured
  uncategorized-transaction handling (`category_filter.filter_transactions`); resolve
  a payee's dominant category for bill naming, tolerating a minority of
  miscategorized outliers via the new `CATEGORY_MAJORITY_THRESHOLD` setting
  (`category_filter.resolve_category_name`). (TASK-006)
- Identify recurring payment patterns per payee (`analyzer.identify_recurring`),
  classifying frequency (monthly, quarterly, half-yearly, yearly, irregular) from
  the median interval between transactions and scoring a confidence value that
  combines occurrence count, interval regularity, and amount consistency, with a
  category-match boost and a configurable penalty (`UNCATEGORIZED_CONFIDENCE_PENALTY`)
  for uncategorized payees. (TASK-003)
- Create bills in Firefly III for approved recurring patterns (`bills_creator.create_bills`),
  computing the amount range from the configured margin and mapping frequency to
  Firefly III's `repeat_freq`. Duplicate bills are detected by a case-sensitive,
  trimmed name match: identical amount range and frequency report "already exists",
  any difference reports "exists with different parameters" with the differing
  values; a server-side name-uniqueness rejection (HTTP 422) is also reported as
  "already exists". Dry-run mode skips all writes; `irregular` patterns are skipped
  unless explicitly forced. (TASK-004)
- Bill names now include the payee's resolved category, e.g. `"Netflix (Subscriptions)"`,
  when a majority category was found (FR-13b); duplicate-bill matching compares
  against this category-aware name. (TASK-008)
- Automated performance benchmark for `analyzer.identify_recurring` (NFR-05),
  run via `make benchmark`: measures elapsed time across synthetic 24-month
  datasets of 500 to 20,000 transactions, prints a summary table, writes
  `benchmark_results.json`, and fails if the largest dataset exceeds the
  60-second bound. At 20,000 transactions the analysis completed in ~0.10s.
  (TASK-009)
- Opt-in, read-only developer script (`make benchmark-real`) to calibrate the
  NFR-05 reference volume against a real Firefly III instance instead of
  synthetic data; never writes to Firefly III. Based on the requirement
  owner's real transaction history (2,207 withdrawal transactions over ~16
  months, extrapolated to ~3,300 over 24 months), NFR-05's reference volume
  is now 5,000 transactions (including a 50% safety margin), replacing the
  provisional 20,000 figure. (TASK-010)
- `python -m firefly_bills_analyzer` now runs the full pipeline end-to-end: fetch
  transactions, filter by category, identify recurring patterns, review and approve
  suggestions in the terminal, then create bills or report them in dry-run mode.
  Without `--auto-approve`, each suggestion is printed and prompted
  `[y]es/[n]o/[a]ll/[q]uit`; with it, entries at or above `HIGH_CONFIDENCE_THRESHOLD`
  are approved automatically. `--dry-run` runs the same review and reports the
  outcomes without writing to Firefly III. Configuration errors and fetch failures
  are surfaced as plain messages, not stack traces. `--clear-cache` is currently a
  no-op with an informational message, since the cache layer (TASK-007) was
  deprioritized for this terminal-only MVP. (TASK-005)
- CSV/JSON export of analysis results (`exporter.export`), controlled by the
  `EXPORT_FORMAT` setting; export path defaults to
  `./firefly-bills-{timestamp}.{csv,json}`. (TASK-005)
- `--help` now documents the key environment variables per run mode
  (`FIREFLY_URL`/`FIREFLY_TOKEN`, `DRY_RUN`, `EXPORT_FORMAT`,
  `HIGH_CONFIDENCE_THRESHOLD`, `INCLUDE_CATEGORIES`/`EXCLUDE_CATEGORIES`,
  `UNCATEGORIZED_BEHAVIOR`) alongside the CLI flags. (TASK-005)

## [0.1.0] - 2026-03-27

### Added

- Requirements specification covering UC1–UC7
- UC1: fetch withdrawal transactions from Firefly III REST API (v1) for a configurable lookback period
- UC2: identify recurring payment patterns per payee, estimating frequency (monthly, quarterly, half-yearly, yearly) and confidence score
- UC3: review and approve suggestions via web UI with sortable table, inline editing of amount, frequency, and start date; CLI fallback with interactive y/n/a prompts and `--auto-approve` flag
- UC4: create bills in Firefly III for approved suggestions, with duplicate detection and configurable amount margin
- UC5: dry-run mode suppressing all writes to Firefly III; export of suggestions to CSV or JSON via web UI button or `EXPORT_FORMAT` env variable
- UC6: category-based filtering via include/exclude lists and configurable confidence boost for transactions matching the include list; uncategorized transaction behavior configurable as include/exclude/neutral
- UC7: file-based disk cache for categories, bills, transactions, and payees with per-dataset configurable TTL; immediate bills cache invalidation on bill creation; manual cache clear via web UI button and `--clear-cache` CLI flag
- Single-page web UI served by built-in Flask or FastAPI HTTP server, with no external CDN dependencies
- REST API endpoints: `GET /api/categories`, `POST /api/analyze`, `POST /api/bills`, `POST /api/export`, `DELETE /api/cache`
- Docker packaging via `Dockerfile` and `docker-compose.yml` with named cache volume and localhost-only port binding
- `.env.example` configuration template covering all parameters
- TrueNAS Scale deployment support

[Unreleased]: https://github.com/your-username/firefly-bills-analyzer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/firefly-bills-analyzer/releases/tag/v0.1.0
