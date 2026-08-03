# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- A pattern's source account name is now resolved from the single distinct
  `source_name` value shared by its transactions, instead of a mode
  computation left over from before FR-32d's source-account partitioning
  made the mode redundant. `source_account_varies` now means something
  actionable: since FR-32d guarantees each pattern's transactions share one
  `source_name` (or none), the flag can only become `True` if that
  partitioning invariant is violated, and doing so now logs a warning
  naming the payee and the conflicting account names rather than silently
  picking a mode. The CLI's existing "(varies)" indicator and the CSV/JSON
  export fields are unchanged in behavior but now read as an anomaly
  signal rather than a normal outcome. (FR-30e, TASK-024)

- `UNCATEGORIZED_CONFIDENCE_PENALTY` is no longer applied to a pattern whose
  amount cluster is fully categorized but for which `resolve_category_name`
  (FR-13b) still resolves no name — e.g. a bill categorized 60/40 across two
  related categories, neither reaching `CATEGORY_MAJORITY_THRESHOLD`. That
  case was previously indistinguishable from a genuinely uncategorized
  cluster and demoted by the same 0.10 penalty, which could be the
  difference between auto-approval and manual review with no indication
  why. The penalty now keys off whether any transaction in the cluster
  carries a category at all (`category_filter.has_any_category()`), not off
  the naming outcome. (TASK-023)

- A bill name's category is now dropped when two or more categories are
  tied for most frequent within the amount cluster it is named from,
  regardless of `CATEGORY_MAJORITY_THRESHOLD`. Previously the tie was
  broken by transaction arrival order from the Firefly III API, so the
  same data could resolve a different category name (and therefore a
  different bill name) across a re-fetch. Locked down with tests covering
  the divergence between cluster-scoped and payee-wide category resolution
  that TASK-012/TASK-014's clustering introduced with no test catching it.
  `resolve_category_name()`'s first parameter is renamed
  `transactions_for_cluster` to state the scope explicitly. (TASK-022)

- Corrected the rationale documented for source-account partitioning
  (FR-32d's docstring in `analyzer.py`): it previously illustrated the need
  for partitioning with a fixed-transfer example that the withdrawal-only
  fetch layer can never actually supply. The docstring now uses the real
  case — the same payee paid from two different source accounts — and
  states the withdrawal-only constraint explicitly. No partitioning
  behavior changed. (TASK-021)

### Added

- Household spend can now be measured per source account and category
  (`HOUSEHOLD_SPEND_CATEGORIES`, comma-separated; empty disables the
  feature): withdrawals in a configured category, or carrying
  `HOUSEHOLD_SPEND_INCLUDE_TAG`, are summed per account, category, and
  calendar month, with the median of the complete months in the analysis
  window reported as the monthly figure alongside its mean, minimum,
  maximum, and month count. A month with no qualifying spending counts as
  zero rather than being omitted, so an account that shops for groceries
  irregularly isn't reported at an inflated average; the first and last
  calendar months of the window, which are partial by construction, never
  contribute a monthly total. A withdrawal already counted as a recurring
  pattern (UC2) is excluded by its own transaction identity, not by payee
  name, so a subscription in a household category is never counted twice.
  A withdrawal above `HOUSEHOLD_SPEND_ONE_OFF_THRESHOLD` (default 2000) is
  reported separately as a one-off purchase instead of distorting the
  monthly figures, and `HOUSEHOLD_SPEND_EXCLUDE_TAG` removes a transaction
  from household spend entirely, overriding every other qualifying rule
  including the include tag. A configured category matching no
  transaction in the window is reported as unmatched. This aggregation
  runs entirely in memory against data already fetched for UC1/UC2 and
  issues no request of its own to Firefly III. (FR-47a-FR-47d, FR-48a-g,
  FR-49a-e, FR-50, TASK-028)

- Detected income sources, and the income accounts an income source could
  not be resolved for, are now written to their own `firefly-income-*` file
  (CSV or JSON, matching `EXPORT_FORMAT`) alongside the recurring-payment
  export, and printed to the CLI before the recurring payment review flow so
  a failed detection is seen before spending attention on bill approvals. An
  account with no qualifying payer or an ambiguous one still gets a row —
  with an empty payer and observed net income, and a `status` column naming
  the reason and the candidate payers considered — so a missing member's
  income is visible in the file rather than only absent from it; a resolved
  income source's row carries `status` `ok`. The exported field list is
  derived from `IncomeSource`'s own dataclass fields rather than hard-coded,
  the same way the pattern export's field list already is. Nothing in this
  path creates a bill or any other Firefly III entity. (FR-45a, FR-45b,
  FR-45c, FR-45d, FR-46, SE-04, TASK-027)

- Deposits fetched for a configured income account are now analyzed to
  recognize the payer who actually pays a monthly income source there:
  deposits are grouped by income account and payer, same-date deposits from
  the same payer are collapsed into one occurrence, and a group qualifies
  once it recurs monthly at least `INCOME_MIN_OCCURRENCES` times. The
  observed net income reported for an account is always the amount of its
  most recent qualifying occurrence, never a mean, so a raise or pay cut is
  visible immediately instead of being smoothed away over the analysis
  window; minimum, maximum, mean, and an outlier count (occurrences
  deviating from the observed figure by more than
  `INCOME_VARIANCE_TOLERANCE`) are reported alongside it so a bonus or
  one-off adjustment shows up rather than being silently absorbed. An
  income account with no qualifying payer, or with more than one, is never
  guessed at: it is reported with every candidate payer's occurrence count
  and frequency instead, so an ambiguous or unpaid account is visible
  rather than defaulted to a picked or summed figure. (FR-41a, FR-41b,
  FR-41c, FR-42a, FR-42b, FR-42c, FR-43, FR-44, TASK-026)

- Deposits landing on one or more configured income accounts
  (`INCOME_ACCOUNTS`, comma-separated) are now fetched from Firefly III
  alongside withdrawal transactions, over the same lookback window and cached
  under their own `deposits` cache key so they don't invalidate or get served
  by the existing transactions cache. Only deposits whose `destination_name`
  matches a configured income account are kept; when `INCOME_ACCOUNTS` is
  unset the fetch is skipped entirely with no network or cache access. The
  fetched deposits are not yet used anywhere in the pipeline — recognizing an
  income source from them, via `INCOME_MIN_OCCURRENCES` and
  `INCOME_VARIANCE_TOLERANCE`, is a follow-up. (FR-39, FR-40, TASK-025)

- Each identified recurring pattern now carries a normalized monthly
  equivalent (its mean amount divided by the fixed divisor for its frequency
  bucket: 1 for monthly, 3 for quarterly, 6 for half-yearly, 12 for yearly),
  so patterns billed at different cadences can be summed into a single
  monthly figure without doing the division by hand after every export.
  Patterns classified `irregular` carry no monthly equivalent. The field
  flows through to both the CSV and JSON export. (TASK-019)

- Amount-cluster splitting now also checks the recurrence interval of any
  transaction that never shares a date with a sibling ("solo" transaction)
  before folding it into the amount cluster it's numerically closest to. If
  2 or more such solo transactions recur on a cadence that disagrees with
  the candidate cluster's own cadence (e.g. a yearly garden-waste charge
  billed through the same payee and account as a quarterly water/garbage
  pair, closest by amount to the quarterly garbage charge), they are split
  into their own cluster instead of being merged in and mislabeled
  "irregular". (TASK-018)

- Transactions can now be filtered by destination payee before
  recurring-payment analysis, via `INCLUDE_PAYEES`/`EXCLUDE_PAYEES`
  (comma-separated, matched against `destination_name`), letting a payee
  whose spending pattern is inherently irregular by design (e.g. a "Cash
  account" destination representing cash withdrawals) be excluded from
  analysis, or the analysis narrowed to specific payees. Exclude is applied
  after include, and transactions without a resolved destination payee never
  match either list. (TASK-017)

- Transactions can now be filtered by source account before recurring-payment
  analysis, via `INCLUDE_ACCOUNTS`/`EXCLUDE_ACCOUNTS` (comma-separated,
  matched against `source_name`), letting an inherently irregular account
  (e.g. a day-to-day groceries account) be excluded from analysis, or the
  analysis narrowed to specific accounts. Exclude is applied after include,
  and transactions without a resolved source account never match either
  list. (TASK-016)

- Recurring-payment identification now partitions a payee's transactions by
  source account before splitting them into amount clusters, so a fixed
  transfer that funds a spending account (e.g. a household budget top-up) is
  never analyzed together with that spending account's own, separately
  variable purchases just because they share a payee name. A same-date
  co-occurrence of differing amounts also no longer splits a group on its
  own unless the same combination of resulting amount clusters recurs across
  at least two distinct dates, so a single day's coincidental double
  purchase (e.g. two grocery runs on the same day) no longer fragments an
  otherwise coherent, continuously variable spending pattern into many
  spurious low-confidence entries. (TASK-014)

- TTL-aware disk cache for transactions and bills (`cache.py`), cutting
  repeated local `--dry-run` runs against a real Firefly III instance from
  minutes (paginated live fetch) down to under a second on a cache hit.
  Transactions are cached per lookback window (changing `LOOKBACK_MONTHS`
  is never served stale-window data); the bills cache is invalidated
  immediately after creating a bill. `--clear-cache` now actually deletes
  cached data instead of printing a no-op message. (TASK-007)

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
