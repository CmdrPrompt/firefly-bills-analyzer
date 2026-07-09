# Requirements Specification: Firefly III Bills Analyzer

**Version:** 0.2.0
**Date:** 2026-07-09
**Status:** Draft, pending owner confirmation of items marked TBD (see Open Items)

## Purpose

Analyze historical transactions in Firefly III to automatically identify recurring payments and create subscription (bill) entries via the API. The goal is to enable cash flow planning across the full year, including low-frequency bills such as quarterly and annual payments.

---

## Definitions

Terms used with a specific meaning in this specification. All requirements use these terms consistently.

| Term | Definition |
| ---- | ---------- |
| Application | The Firefly III Bills Analyzer software as a whole, including CLI mode |
| Web UI | The browser-based user interface served by the application's built-in web server |
| Web server | The built-in HTTP server component of the application |
| firefly-python-api | The standalone, shared Python package that owns the HTTP session toward Firefly III |
| Recurring payment pattern | A group of transactions with the same payee that meets the occurrence threshold (FR-04a) |
| Frequency | The classification of a recurring payment pattern by median interval: monthly, quarterly, half-yearly, yearly, or irregular (FR-03) |
| Confidence score | The value in [0.0, 1.0] computed per FR-27 |
| Neutral (uncategorized behavior) | Uncategorized transactions are included in the analysis but receive no confidence boost and no penalty **[DEFINITION TBD: confirm with owner]** |
| Common error | An error in the enumerated list: unreachable Firefly III instance, invalid or expired API token, invalid configuration value **[LIST TBD: confirm completeness with owner]** |
| Duplicate bill | An existing bill in Firefly III whose name equals the candidate bill name **[CRITERION TBD: confirm whether amount or frequency shall also match]** |

---

## Actors

| Actor       | Description                                                                 |
| ----------- | --------------------------------------------------------------------------- |
| User        | Interacts via web browser or runs the application manually or on a schedule |
| Web server  | Flask/FastAPI app that exposes the UI and orchestrates UC1–UC7              |
| Firefly III | Source system for transactions and target system for bills                  |

---

## Use Cases

The use cases are informative. They describe intended flows and provide context for the requirements. Binding obligations are stated only in the Functional Requirements, Non-functional Requirements, and Scope Exclusions sections.

### UC1: Fetch transaction history

**Actor:** Application
**Precondition:** Valid API token and reachable Firefly III instance
**Flow:**

1. The application calls the Firefly III REST API and fetches transactions for a configurable time window (default: 24 months)
2. Only outgoing transactions (withdrawals) are fetched
3. Transactions are held in memory for further analysis

**Alternative flow:**

- API unreachable: application exits with an error message

---

### UC2: Identify recurring payments

**Actor:** Application
**Precondition:** Transaction history fetched (UC1)
**Flow:**

1. Transactions are grouped by payee (`destination_name`)

2. For each group the following are calculated:

   - Number of occurrences
   - Average amount (min/max)
   - Median number of days between transactions
   - Most common day of the month/quarter/year

3. A pattern is classified as recurring if it meets a configurable threshold (default: at least 2 occurrences)

4. Frequency is estimated by comparing the median interval between transactions to the following thresholds:

   | Frequency   | Median interval (days)   |
   | ----------- | ------------------------ |
   | Monthly     | 25–35                    |
   | Quarterly   | 80–100                   |
   | Half-yearly | 160–200                  |
   | Yearly      | 340–390                  |
   | Irregular   | outside all ranges above |

5. A confidence score in [0.0, 1.0] is computed as: `confidence = 0.4 × occurrence_score + 0.4 × regularity_score + 0.2 × amount_score + category_boost` where:

   - `occurrence_score = min(n / 4, 1.0)`
   - `regularity_score = max(0, 1 − stddev_days / median_days)`
   - `amount_score = max(0, 1 − stddev_amount / mean_amount)`
   - `category_boost = CATEGORY_CONFIDENCE_BOOST` if the payee's category is in the include list, else 0

6. Results are returned to the caller (web server or terminal) with the confidence score per entry

**Alternative flow:**

- Too few transactions to establish a pattern: entry is flagged with low confidence

---

### UC3: Review and approve suggestions

**Actor:** User
**Precondition:** Analysis completed (UC2)
**Primary flow (web UI):**

1. The web UI displays the analysis results in a sortable table
2. Each row shows: payee name, category, estimated amount (min–max), frequency, next due date, confidence score
3. High-confidence rows are pre-selected; others are unchecked
4. The user can edit amount, frequency, and start date inline per row
5. The user clicks "Create selected bills" to trigger UC4
6. The outcome of UC4 is shown inline (created / already exists / error)

**Alternative flow (terminal, `--auto-approve`):**

- All entries above the confidence threshold are approved without interaction
- Remaining entries are rejected or presented interactively row by row (y/n/a)

---

### UC4: Create bills in Firefly III

**Actor:** Application
**Precondition:** At least one entry approved (UC3)
**Flow:**

1. The application creates a bill via the Firefly III API for each approved entry with:
   - Name (payee name)
   - Amount range (min/max with configurable margin, default: ±10%)
   - Frequency and start date
   - Active status
2. Existing bills are checked before creation to avoid duplicates
3. Created bills are logged

**Alternative flow:**

- Bill already exists: application skips it and notifies the user

---

### UC5: Run in report mode (dry-run)

**Actor:** User
**Precondition:** Transaction history available
**Primary flow (web UI):**

1. The user enables the dry-run toggle in the UI before running the analysis
2. Analysis results and suggestions are displayed in the table as normal
3. The "Create selected bills" button is replaced by "Export"; nothing is written to Firefly III
4. The user can export suggestions as CSV or JSON via button

**Alternative flow (terminal):**

1. The application is run with the `--dry-run` flag
2. Analysis and suggestions are printed to the terminal
3. No bills are created in Firefly III
4. Suggestions are exported according to `EXPORT_FORMAT`

---

### UC6: Filter and weight analysis using categories

**Actor:** Application / User
**Precondition:** Transaction history fetched (UC1), categories available in Firefly III
**Primary flow (web UI):**

1. The web UI fetches all existing categories from the Firefly III API on page load
2. The user selects categories to include or exclude via multiselect lists
3. The user selects the behavior for uncategorized transactions via a dropdown
4. Selections are stored in the session and applied when the analysis runs

**Alternative flow (terminal / .env):**

1. If `INCLUDE_CATEGORIES` is set, only transactions with a matching category are included
2. If `EXCLUDE_CATEGORIES` is set, transactions with a matching category are excluded
3. Uncategorized transactions are handled according to `UNCATEGORIZED_BEHAVIOR`

**Common to both flows:**

- Transactions whose category appears in the include list receive a confidence boost (`CATEGORY_CONFIDENCE_BOOST`)
- The category name is shown in the table and used to supplement the payee name when naming bills
- If no categories are selected, the analysis runs without filtering or weighting

---

### UC7: Manage local data cache

**Actor:** Application / User
**Precondition:** Application is running
**Primary flow (automatic cache):**

1. On the first call to `/api/categories`, data is fetched from Firefly III and saved to a file cache with a timestamp
2. Subsequent calls within `CACHE_TTL_CATEGORIES` read from cache without making an API call
3. On calls to `/api/analyze`, the application checks whether cached transaction data exists and is within `CACHE_TTL_TRANSACTIONS`; if so, cached data is used, otherwise fresh data is fetched
4. When UC4 creates a new bill, the bills cache is invalidated immediately

**Primary flow (manual clear via web UI):**

1. The user clicks "Clear cache" in the web UI
2. All cache files are deleted
3. The next API call fetches fresh data from Firefly III

**Alternative flow (CLI):**

- The `--clear-cache` flag clears all cache files on startup

**Cached data sets:**

| Data           | Cache level | Default TTL |
| -------------- | ----------- | ----------- |
| Categories     | File        | 24h         |
| Existing bills | File        | 1h          |
| Transactions   | File        | 1h          |
| Payees         | File        | 24h         |

---

## Functional Requirements

Requirements follow EARS-style patterns with the system (or subsystem) as active subject. Decomposed requirements retain the original ID with an a/b suffix. Trace column references the use case each requirement is derived from.

| ID     | Requirement | Trace |
| ------ | ----------- | ----- |
| FR-01  | The application shall communicate with Firefly III via REST API (v1) exclusively through the shared `firefly-python-api` package, which provides an authenticated session, URL validation, and configuration loading | UC1, UC4 |
| FR-02  | The application shall read the analysis time window from configuration, with a default of 24 months | UC1 |
| FR-03  | The application shall classify each recurring payment pattern into exactly one of the frequencies monthly, quarterly, half-yearly, yearly, or irregular | UC2 |
| FR-04a | The application shall read the confidence threshold for automatic approval from configuration (`HIGH_CONFIDENCE_THRESHOLD`, default 0.80) | UC3 |
| FR-04b | The application shall read the minimum occurrence threshold for classifying a pattern as recurring from configuration (`MIN_OCCURRENCES`, default 2) | UC2 |
| FR-05  | When the application is about to create a bill, the application shall verify whether a duplicate bill (see Definitions) already exists in Firefly III before creating the bill | UC4 |
| FR-06  | When the application creates a bill, the application shall compute the bill amount range (minimum and maximum) by applying the configured margin (`AMOUNT_MARGIN`) to the estimated amount | UC4 |
| FR-07a | When the application is started with the `--dry-run` flag or the `DRY_RUN` configuration parameter is set, the application shall activate dry-run mode | UC5 |
| FR-07b | While dry-run mode is active, the application shall not write any data to Firefly III | UC5 |
| FR-08  | Upon user request, the application shall export the analysis results to CSV format or JSON format | UC5 |
| FR-09  | The application shall log all API calls and their outcomes | UC1, UC4 |
| FR-10  | The application shall read its configuration from a `.env` file or from environment variables; when the same parameter is defined in both, environment variables shall take precedence **[PRECEDENCE TBD: confirm with owner]** | — |
| FR-11a | When a category include list is configured, the application shall include only transactions whose category matches the include list in the analysis | UC6 |
| FR-11b | When a category exclude list is configured, the application shall exclude transactions whose category matches the exclude list from the analysis | UC6 |
| FR-12  | When a transaction's category appears in the include list, the application shall increase that transaction's confidence score by the configured category confidence boost (`CATEGORY_CONFIDENCE_BOOST`) | UC6 |
| FR-13a | The web UI shall display the category name in the table view | UC6 |
| FR-13b | When exactly one category occurs among a payee's transactions, the application shall include that category name in the bill name | UC6 |
| FR-14  | The application shall process uncategorized transactions according to the configured behavior (`UNCATEGORIZED_BEHAVIOR`), where the configured behavior is one of include, exclude, or neutral (see Definitions) | UC6 |
| FR-15  | The application shall expose a web UI via a built-in HTTP server | UC3 |
| FR-16  | When the web UI page is loaded, the web UI shall fetch the existing categories from the Firefly III API and display them as multiselect lists | UC6 |
| FR-17a | When an analysis completes, the web UI shall display the analysis results in a sortable table | UC3 |
| FR-17b | The web UI shall accept inline edits of amount, frequency, and start date for each analysis result row | UC3 |
| FR-18  | When bill creation completes, the web UI shall display the outcome per bill (created, already exists, or error) without reloading the page | UC3 |
| FR-19  | When the user enables the dry-run toggle in the web UI, the web UI shall activate dry-run mode | UC5 |
| FR-20  | When the user clicks the export button in the web UI, the application shall export the analysis results to CSV format or JSON format | UC5 |
| FR-21  | The application shall cache categories, bills, transactions, and payees as JSON files on disk | UC7 |
| FR-22  | The application shall read a separate cache TTL from configuration for each cached data set (categories, bills, transactions, payees) | UC7 |
| FR-23  | When the application creates a new bill, the application shall invalidate the bills cache synchronously within the same creation operation, before the creation response is returned | UC7 |
| FR-24a | The web UI shall display a "Clear cache" button | UC7 |
| FR-24b | When the user clicks the "Clear cache" button, the application shall delete all cached data | UC7 |
| FR-25  | When the application is started in CLI mode with the `--clear-cache` flag, the application shall delete all cache files during startup | UC7 |
| FR-26a | The `firefly-python-api` package shall read `FIREFLY_URL` and `FIREFLY_TOKEN` from environment variables or from a `.env` file, with the same precedence rule as FR-10 | — |
| FR-26b | The `firefly-python-api` package shall expose a `FireflyClient` class that provides a configured `requests.Session` | — |
| FR-27  | When the application classifies recurring payment patterns, the application shall compute the confidence score as 0.4 × occurrence score + 0.4 × regularity score + 0.2 × amount score + category boost, and shall clamp the result to the range [0.0, 1.0] | UC2 |

---

## Non-functional Requirements

| ID      | Requirement | Trace |
| ------- | ----------- | ----- |
| NFR-01  | The application shall be written in Python 3.10+ | — |
| NFR-02  | The application shall use no external runtime dependencies other than `requests`, `python-dotenv`, and the selected web framework (`Flask` or `FastAPI`) **[FRAMEWORK TBD: select one; see Open Items]** | — |
| NFR-03  | When a Firefly III API response is paginated, the application shall fetch all pages and aggregate the results before returning them to the caller | UC1 |
| NFR-04  | If a common error (see Definitions) occurs, then the application shall display an error message that states the cause of the error, and shall not include a stack trace in the message | UC1 |
| NFR-05  | When the user starts an analysis of 24 months of transaction data (reference volume: **[VALUE TBD]** transactions), the application shall complete the analysis within 60 seconds | UC2 |
| NFR-06  | The web UI shall load all of its assets from the local web server and shall not fetch any asset from an external CDN | UC3 |
| NFR-07a | The web server shall listen on the port configured via `WEB_PORT`, with a default port of 5000 | — |
| NFR-07b | The web server shall bind to the address configured via `WEB_HOST`, with a default bind address of `127.0.0.1`, including support for the value `0.0.0.0` | — |
| NFR-08  | *Reserved. Not used, retained to keep the ID sequence stable against version 0.1.0* | — |
| NFR-09  | The application shall retain the cache directory and its contents across application restarts | UC7 |
| NFR-10  | `firefly-python-api` shall be a standalone, pip-installable package shared with `firefly-bank-importer` | — |
| NFR-11  | The `firefly-python-api` package shall declare no runtime dependencies other than `requests` and `python-dotenv` | — |

---

## Scope Exclusions

Binding negative requirements defining the boundary of version 1.0. These are intentional exclusions and shall be verified as such.

| ID     | Requirement |
| ------ | ----------- |
| SE-01  | The application shall not create categories or budgets in Firefly III |
| SE-02  | The application shall not create a bill for an entry whose confidence score is below the configured confidence threshold, unless the user explicitly approves the entry |
| SE-03  | The application shall not delete or update existing bills in Firefly III |

Note on SE-02: version 0.1.0 equated "irregular pattern" with "confidence below threshold". These are distinct concepts (frequency is interval-based per FR-03; confidence is score-based per FR-27). SE-02 is expressed in terms of confidence, which matches the approval logic in UC3.

---

## Architecture

### Project structure

```
firefly_bills_analyzer/
├── app.py               # Flask/FastAPI app, HTTP endpoints, starts web server
├── analyzer.py          # UC1 + UC2: fetch transactions, identify patterns
├── category_filter.py   # UC6: filter and weight by category
├── bills_creator.py     # UC4: create bills via Firefly III API
├── cache.py             # UC7: read/write/invalidate JSON cache files
├── exporter.py          # UC5: CSV/JSON export
├── config.py            # Reads .env and environment variables
├── templates/
│   └── index.html       # Single-page web UI
├── static/
│   └── app.js           # Minimal vanilla JS for table interactions and API calls
├── cache/               # Cache files (created automatically, persisted across restarts)
│   ├── categories.json
│   ├── bills.json
│   ├── transactions.json
│   └── payees.json
├── .env.example         # Configuration template without sensitive values
└── requirements.txt     # Python dependencies
```

### Shared Firefly client

The HTTP layer toward Firefly III is provided by a standalone Python package
(`firefly-python-api`) shared between `firefly-bills-analyzer` and `firefly-bank-importer`. It exposes:

- `FireflyClient(url, token)` — wraps `requests.Session` with Bearer auth headers
- `load_config(env_path)` — reads `FIREFLY_URL` and `FIREFLY_TOKEN` from environment or `.env` file
- `validate_connection()` — `GET /api/v1/about`; raises on failure

The package owns no application logic; it only manages the HTTP session lifecycle and credential loading.

### Endpoints

| Method   | Endpoint          | Description                                             |
| -------- | ----------------- | ------------------------------------------------------- |
| `GET`    | `/`               | Serves the web UI                                       |
| `GET`    | `/api/categories` | Returns categories (from cache or Firefly III)          |
| `POST`   | `/api/analyze`    | Runs UC1, UC2, and UC6; returns suggestions as JSON     |
| `POST`   | `/api/bills`      | Creates approved bills (UC4); returns outcome per entry |
| `POST`   | `/api/export`     | Exports suggestions to CSV or JSON (UC5)                |
| `DELETE` | `/api/cache`      | Clears all cached data (UC7)                            |

### Web UI flow

```
Page load
  → GET /api/categories → populates multiselect lists

User configures filters + clicks "Run analysis"
  → POST /api/analyze → table rendered with suggestions

User adjusts rows + clicks "Create selected bills"
  → POST /api/bills → outcome shown per row in the table
```

### Run modes

The application supports two run modes:

- **Web mode** (default): `python app.py` starts the HTTP server
- **CLI mode**: `python app.py --cli [--dry-run] [--auto-approve] [--clear-cache]` runs without a web server

---

## Configuration Parameters

| Parameter                   | Description                                                      | Default         |
| --------------------------- | ---------------------------------------------------------------- | --------------- |
| `FIREFLY_URL`               | Base URL of the Firefly III instance                             | *(required)*    |
| `FIREFLY_TOKEN`             | Personal Access Token                                            | *(required)*    |
| `LOOKBACK_MONTHS`           | Months of transaction history to analyze                         | `24`            |
| `MIN_OCCURRENCES`           | Minimum occurrences to classify as recurring                     | `2`             |
| `AMOUNT_MARGIN`             | Margin for min/max amount (fraction)                             | `0.10`          |
| `HIGH_CONFIDENCE_THRESHOLD` | Confidence threshold for auto-approval in CLI mode               | `0.80`          |
| `DRY_RUN`                   | Do not create any bills                                          | `false`         |
| `EXPORT_FORMAT`             | Export format (csv/json/none)                                    | `none`          |
| `INCLUDE_CATEGORIES`        | Comma-separated category include list                            | *(empty = all)* |
| `EXCLUDE_CATEGORIES`        | Comma-separated category exclude list                            | *(empty)*       |
| `CATEGORY_CONFIDENCE_BOOST` | Confidence boost for transactions matching the include list      | `0.15`          |
| `UNCATEGORIZED_BEHAVIOR`    | Handling of uncategorized transactions (include/exclude/neutral) | `neutral`       |
| `WEB_PORT`                  | Port the web server listens on                                   | `5000`          |
| `WEB_HOST`                  | IP address the web server binds to                               | `127.0.0.1`     |
| `CACHE_DIR`                 | Directory for cache files                                        | `./cache`       |
| `CACHE_TTL_CATEGORIES`      | TTL for category cache (seconds)                                 | `86400`         |
| `CACHE_TTL_BILLS`           | TTL for bills cache (seconds)                                    | `3600`          |
| `CACHE_TTL_TRANSACTIONS`    | TTL for transaction cache (seconds)                              | `3600`          |
| `CACHE_TTL_PAYEES`          | TTL for payee cache (seconds)                                    | `86400`         |

---

## Open Items

Decisions required from the requirement owner before this specification is baselined.

| # | Item | Affected requirements |
| - | ---- | --------------------- |
| 1 | Duplicate bill matching criterion: name only, or name plus amount/frequency | FR-05, Definitions |
| 2 | Definition of "neutral" uncategorized behavior | FR-14, Definitions |
| 3 | Enumerated list of "common errors" | NFR-04, Definitions |
| 4 | Configuration source precedence (environment variables over `.env` proposed) | FR-10, FR-26a |
| 5 | Web framework selection: Flask or FastAPI | NFR-02 |
| 6 | Reference transaction volume for the 60-second performance bound | NFR-05 |
| 7 | Confirm FR-13b interpretation: "unique per payee" = exactly one category among the payee's transactions | FR-13b |
| 8 | Confirm obligation levels raised or made explicit during review (all reformulated requirements use "shall") | All |

---

## Changelog

### 0.2.0 (2026-07-09)

Rework based on ISO/IEC/IEEE 29148 review of version 0.1.0:

- All requirements reformulated with the system as active subject in active voice, EARS-style patterns
- Compound requirements decomposed: FR-07, FR-11, FR-13, FR-17, FR-24, FR-26, NFR-07 split into a/b
- FR-04 split into FR-04a (confidence threshold) and FR-04b (occurrence threshold, previously only implicit in UC2)
- Weak verbs (support, handle, work) replaced with verifiable strong verbs
- "immediately" in FR-23 replaced with synchronous invalidation semantics
- Constraints section replaced by binding Scope Exclusions (SE-01 to SE-03); irregular/confidence terminology reconciled in SE-02
- Definitions section added; "the shared package" normalized to `firefly-python-api`
- Trace column added linking requirements to use cases
- NFR-08 marked reserved to keep the ID sequence stable
- Open Items section added for all TBD decisions

### 0.1.0 (2026-03-27)

Initial version.

---

## Dependencies

- Firefly III v6+ with REST API enabled
- Personal Access Token with read and write access
- `firefly-python-api` (shared internal package) — authenticated HTTP session and URL/token configuration
- Flask or FastAPI (web server)