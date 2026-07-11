# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
