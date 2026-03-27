# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
