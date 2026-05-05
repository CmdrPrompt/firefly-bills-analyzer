# Requirements Specification: Firefly III Bills Analyzer

**Version:** 0.1.0  
**Date:** 2026-03-27

## Purpose

Analyze historical transactions in Firefly III to automatically identify recurring payments and create subscription (bill) entries via the API. The goal is to enable cash flow planning across the full year, including low-frequency bills such as quarterly and annual payments.

---

## Actors

| Actor | Description |
|---|---|
| User | Interacts via web browser or runs the application manually or on a schedule |
| Web server | Flask/FastAPI app that exposes the UI and orchestrates UC1–UC7 |
| Firefly III | Source system for transactions and target system for bills |

---

## Use Cases

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

   | Frequency | Median interval (days) |
   |---|---|
   | Monthly | 25–35 |
   | Quarterly | 80–100 |
   | Half-yearly | 160–200 |
   | Yearly | 340–390 |
   | Irregular | outside all ranges above |

5. A confidence score in [0.0, 1.0] is computed as:
   `confidence = 0.4 × occurrence_score + 0.4 × regularity_score + 0.2 × amount_score + category_boost`
   where:
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

| Data | Cache level | Default TTL |
|---|---|---|
| Categories | File | 24h |
| Existing bills | File | 1h |
| Transactions | File | 1h |
| Payees | File | 24h |

---

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | The application shall communicate with Firefly III via REST API (v1) exclusively through the shared `firefly-python-api` package, which provides an authenticated session, URL validation, and configuration loading |
| FR-02 | The analysis time window shall be configurable (default: 24 months) |
| FR-03 | The application shall support the frequencies: monthly, quarterly, half-yearly, yearly, irregular |
| FR-04 | The confidence threshold for automatic approval shall be configurable |
| FR-05 | The application shall check whether a bill already exists before creating it |
| FR-06 | The amount range (min/max) shall be calculated with a configurable margin |
| FR-07 | Dry-run mode shall be supported via a flag and shall not write anything to Firefly III |
| FR-08 | Results shall be exportable to CSV or JSON |
| FR-09 | The application shall log all API calls and their outcomes |
| FR-10 | Configuration shall be handled via a `.env` file or environment variables |
| FR-11 | The application shall support an include list and an exclude list for categories |
| FR-12 | Transactions whose category appears in the include list shall receive a configurable confidence boost |
| FR-13 | The category name shall be shown in the table view and included in the bill name if unique per payee |
| FR-14 | The behavior for uncategorized transactions shall be configurable (include/exclude/neutral) |
| FR-15 | The application shall expose a web UI via a built-in HTTP server |
| FR-16 | The web UI shall fetch existing categories from the Firefly III API and present them as multiselect lists |
| FR-17 | Analysis results shall be shown in a sortable table with inline editing of amount, frequency, and start date |
| FR-18 | The web UI shall show the outcome of bill creation (created / already exists / error) without a page reload |
| FR-19 | Dry-run mode shall be activatable via a toggle in the web UI |
| FR-20 | Export of analysis results (CSV/JSON) shall be triggerable via a button in the web UI |
| FR-21 | The application shall cache categories, bills, transactions, and payees as JSON files on disk |
| FR-22 | TTL shall be separately configurable per data set |
| FR-23 | The bills cache shall be invalidated immediately when a new bill is created via UC4 |
| FR-24 | The web UI shall expose a "Clear cache" button that removes all cached data |
| FR-25 | CLI mode shall support the `--clear-cache` flag to clear the cache on startup |
| FR-26 | The `firefly-python-api` package shall read `FIREFLY_URL` and `FIREFLY_TOKEN` from environment variables or a `.env` file and expose a `FireflyClient` class with a configured `requests.Session` |
| FR-27 | The confidence score shall be computed from occurrence count (weight 0.4), interval regularity (weight 0.4), and amount stability (weight 0.2), with an optional category boost; the result shall be clamped to [0.0, 1.0] |

---

## Non-functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | The application shall be written in Python 3.10+ |
| NFR-02 | External dependencies shall be kept minimal; `requests`, `python-dotenv`, and `Flask` or `FastAPI` are sufficient |
| NFR-03 | The application shall handle Firefly III API pagination transparently |
| NFR-04 | Error handling shall produce clear error messages without stack traces for common errors |
| NFR-05 | Analysis of 24 months of data shall complete in under 60 seconds |
| NFR-06 | The web UI shall work without external CDN dependencies (all assets served locally) |
| NFR-07 | The web server shall listen on a configurable port (default: 5000) and configurable bind address (default: `127.0.0.1`); to allow access from other machines the bind address shall be settable to `0.0.0.0` via `WEB_HOST` |
| NFR-09 | The cache directory shall persist across application restarts |
| NFR-10 | `firefly-python-api` shall be a standalone, pip-installable package shared with `firefly-bank-importer` |
| NFR-11 | The shared package shall have no opinionated dependencies beyond `requests` and `python-dotenv` |

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
(`firefly-python-api`) shared between `firefly-bills-analyzer` and
`firefly-bank-importer`. It exposes:

- `FireflyClient(url, token)` — wraps `requests.Session` with Bearer auth headers
- `load_config(env_path)` — reads `FIREFLY_URL` and `FIREFLY_TOKEN` from environment or `.env` file
- `validate_connection()` — `GET /api/v1/about`; raises on failure

The package owns no application logic; it only manages the HTTP session lifecycle and credential loading.

---

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the web UI |
| `GET` | `/api/categories` | Returns categories (from cache or Firefly III) |
| `POST` | `/api/analyze` | Runs UC1, UC2, and UC6; returns suggestions as JSON |
| `POST` | `/api/bills` | Creates approved bills (UC4); returns outcome per entry |
| `POST` | `/api/export` | Exports suggestions to CSV or JSON (UC5) |
| `DELETE` | `/api/cache` | Clears all cached data (UC7) |

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

| Parameter | Description | Default |
|---|---|---|
| `FIREFLY_URL` | Base URL of the Firefly III instance | *(required)* |
| `FIREFLY_TOKEN` | Personal Access Token | *(required)* |
| `LOOKBACK_MONTHS` | Months of transaction history to analyze | `24` |
| `MIN_OCCURRENCES` | Minimum occurrences to classify as recurring | `2` |
| `AMOUNT_MARGIN` | Margin for min/max amount (fraction) | `0.10` |
| `HIGH_CONFIDENCE_THRESHOLD` | Confidence threshold for auto-approval in CLI mode | `0.80` |
| `DRY_RUN` | Do not create any bills | `false` |
| `EXPORT_FORMAT` | Export format (csv/json/none) | `none` |
| `INCLUDE_CATEGORIES` | Comma-separated category include list | *(empty = all)* |
| `EXCLUDE_CATEGORIES` | Comma-separated category exclude list | *(empty)* |
| `CATEGORY_CONFIDENCE_BOOST` | Confidence boost for transactions matching the include list | `0.15` |
| `UNCATEGORIZED_BEHAVIOR` | Handling of uncategorized transactions (include/exclude/neutral) | `neutral` |
| `WEB_PORT` | Port the web server listens on | `5000` |
| `WEB_HOST` | IP address the web server binds to | `127.0.0.1` |
| `CACHE_DIR` | Directory for cache files | `./cache` |
| `CACHE_TTL_CATEGORIES` | TTL for category cache (seconds) | `86400` |
| `CACHE_TTL_BILLS` | TTL for bills cache (seconds) | `3600` |
| `CACHE_TTL_TRANSACTIONS` | TTL for transaction cache (seconds) | `3600` |
| `CACHE_TTL_PAYEES` | TTL for payee cache (seconds) | `86400` |

---

## Constraints

- The application does not create categories or budgets in Firefly III
- Transactions with an irregular pattern (confidence below the minimum threshold) are reported but do not result in bill creation without explicit approval
- The application does not handle deletion or updating of existing bills

---

## Dependencies

- Firefly III v6+ with REST API enabled
- Personal Access Token with read and write access
- `firefly-python-api` (shared internal package) — authenticated HTTP session and URL/token configuration
- Flask or FastAPI (web server)
