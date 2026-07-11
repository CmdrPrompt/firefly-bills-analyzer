# Requirements Specification: Firefly III Bills Analyzer

**Version:** 0.2.17
**Date:** 2026-07-11
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
| Recurring payment pattern | A group of transactions with the same payee and, when the payee's transactions form more than one amount cluster (FR-32a, FR-32d), the same amount cluster, that meets the occurrence threshold (FR-04a) |
| Amount cluster | A subgroup of a payee's transactions, formed by first partitioning the payee group by source account (FR-32d), then applying FR-32a independently within each source-account subgroup: amounts observed on co-occurrence dates (dates with two or more differing amounts) are clustered via a tolerance-based gap split, and every transaction in the subgroup is extended to whichever resulting cluster's mean is numerically closest — but only when the split is corroborated (FR-32a) by the same cluster combination recurring across two or more distinct co-occurrence dates. A subgroup with no co-occurrence date, or whose co-occurrence dates never share a repeating cluster combination, forms a single amount cluster regardless of how much its amount varies — this is what keeps a single bill whose amount fluctuates over time (e.g. a metered utility bill priced by season and consumption), or an account whose spending is continuously variable and rarely repeats an exact amount (e.g. day-to-day grocery purchases from a dedicated spending account), from being fragmented merely because two transactions once landed on the same date. A subgroup where the same combination of differing amounts genuinely recurs together (e.g. two household members billed the same fee, or several subscriptions billed through the same merchant, landing on the same date every cycle) splits into more than one amount cluster |
| Billing event | Within an amount cluster, one or more transactions that share the exact same date, collapsed per FR-33a into a single unit whose amount is their sum. Occurrence counts, interval calculation, and amount statistics (UC2) operate on billing events, not raw transaction rows. Budget-wise, several same-day transactions for the same recurring charge (e.g. one household member's invoice and another's, billed together) represent one combined outflow, not two independent cycle points |
| Frequency | The classification of a recurring payment pattern by median interval: monthly, quarterly, half-yearly, yearly, or irregular (FR-03) |
| Confidence score | The value in [0.0, 1.0] computed per FR-27 |
| Neutral (uncategorized behavior) | Uncategorized transactions are always included in the analysis (never filtered out, regardless of `INCLUDE_CATEGORIES`/`EXCLUDE_CATEGORIES`), receive no `CATEGORY_CONFIDENCE_BOOST`, and have `UNCATEGORIZED_CONFIDENCE_PENALTY` subtracted from their pattern's confidence score per FR-27 |
| Common error | An error in the enumerated list: unreachable Firefly III instance, invalid or expired API token, invalid or missing required configuration value, insufficient API token permissions, Firefly III API error response (4xx/5xx other than 401, 403, and the name-uniqueness rejection handled per FR-05d), cache directory not writable. Example messages for each are given in Error Messages |
| Duplicate bill | An existing bill in Firefly III whose name equals the candidate bill name, compared case-sensitively after trimming leading and trailing whitespace. Amount and frequency are not part of the duplicate criterion |

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
3. In CLI mode, a progress bar is displayed showing pages fetched out of the
   total (FR-34), driven by `firefly-python-api`'s per-page progress callback
4. Transactions are held in memory for further analysis

**Alternative flow:**

- API unreachable: application exits with an error message

---

### UC2: Identify recurring payments

**Actor:** Application
**Precondition:** Transaction history fetched (UC1)
**Flow:**

1. Transactions are grouped by payee (`destination_name`)

2. Each payee group is first partitioned by source account (FR-32d), then each
   source-account subgroup is further split into amount clusters (FR-32a) based on
   corroborated same-date co-occurrence, not on amount variance alone:

   a. Transactions sharing the same `source_name` value form one subgroup; transactions
      with no `source_name` form their own subgroup. Distinct financial roles — e.g. a
      fixed transfer from a household account into a dedicated spending account, versus
      the spending itself — are typically withdrawn through different source accounts, so
      partitioning here first keeps such transfers from being amount-clustered together
      with the spending they fund
   b. Within each source-account subgroup, transactions are grouped by date. A date on
      which two or more transactions have *differing* amounts is a co-occurrence date
   c. The amounts observed at co-occurrence dates are clustered using a tolerance-based
      gap split (sort ascending, start a new candidate cluster whenever the gap to the
      previous amount exceeds `AMOUNT_CLUSTER_TOLERANCE` of the smaller of the two); for
      each co-occurrence date, record which candidate cluster(s) its amounts fall into
      (its "signature")
   d. If the subgroup has no co-occurrence date, or if no signature spanning two or more
      candidate clusters is shared by two or more distinct co-occurrence dates, the whole
      subgroup remains a single amount cluster, regardless of how much its amount varies
      across different dates. This is what keeps a single bill whose amount fluctuates
      over time — e.g. a metered utility bill priced by season and consumption — or an
      account whose spending is continuously variable and rarely repeats an exact amount
      — e.g. day-to-day grocery purchases from a dedicated spending account — from being
      fragmented into artificial sub-clusters merely because two transactions once landed
      on the same date. This reveals that the payee genuinely bundles more than one
      simultaneous, recurring charge (e.g. two household members billed the same fee, or
      several subscriptions billed through the same merchant, landing on the same date
      every cycle) only when that pattern repeats
   e. Otherwise, every transaction in the subgroup — including ones not on a co-occurrence
      date — is assigned to whichever candidate cluster's mean amount is numerically
      closest to its own amount

   Every step below operates on the resulting payee/source-account/amount-cluster group,
   not the raw payee group

3. Within each payee/amount-cluster group, transactions that share the exact same date are
   collapsed into a single billing event (FR-33a) whose amount is their sum. Budget-wise,
   several same-day transactions for the same recurring charge (e.g. one household member's
   invoice and another's, billed together) represent one combined outflow — treating them as
   separate cycle points would otherwise corrupt the interval calculation in step 5. All
   subsequent steps operate on the resulting billing events, not the pre-collapse transaction
   rows; source account resolution (FR-30a) is unaffected and continues to consider every
   underlying transaction

4. For each payee/amount-cluster group the following are calculated over its billing events:

   - Number of occurrences (billing events)
   - Average amount (min/max)
   - Median number of days between billing events
   - Most common day of the month/quarter/year
   - Source account: the account name (`source_name`) that occurs most often among
     the group's underlying transactions, plus whether more than one distinct source account
     occurs in the group (FR-30a)

5. A pattern is classified as recurring if it meets a configurable threshold (default: at least 2 occurrences)

6. Frequency is estimated by comparing the median interval between billing events to the following thresholds:

   | Frequency   | Median interval (days)   |
   | ----------- | ------------------------ |
   | Monthly     | 25–35                    |
   | Quarterly   | 80–100                   |
   | Half-yearly | 160–200                  |
   | Yearly      | 340–390                  |
   | Irregular   | outside all ranges above |

7. A confidence score in [0.0, 1.0] is computed as: `confidence = 0.4 × occurrence_score + 0.4 × regularity_score + 0.2 × amount_score + category_boost − uncategorized_penalty` where:

   - `occurrence_score = min(n / 4, 1.0)`
   - `regularity_score = max(0, 1 − stddev_days / median_days)`
   - `amount_score = max(0, 1 − stddev_amount / mean_amount)`
   - `category_boost = CATEGORY_CONFIDENCE_BOOST` if the payee's category is in the include list, else 0
   - `uncategorized_penalty = UNCATEGORIZED_CONFIDENCE_PENALTY` if the payee has no category and `UNCATEGORIZED_BEHAVIOR` is `neutral`, else 0

8. When a payee produces more than one amount cluster, each cluster's bill name is
   disambiguated by appending its representative (mean) amount, so that distinct clusters
   never collide under FR-05a's name-only duplicate check (FR-32c)

9. Results are returned to the caller (web server or terminal) with the confidence score per entry

**Alternative flow:**

- Too few transactions to establish a pattern: entry is flagged with low confidence
- A payee's transactions all share one source account and form only one amount cluster (the
  common case): behavior is unchanged from the pre-FR-32/FR-32d grouping
- A payee's transactions span more than one source account but no subgroup's co-occurrence
  is corroborated: each source-account subgroup is analyzed as its own single-cluster
  pattern (e.g. a fixed transfer into a spending account, and the spending account's
  purchases, become two separate patterns)
- No two transactions in a cluster share the exact same date: behavior is unchanged from the
  pre-FR-33 per-transaction calculation (every transaction is its own billing event)

---

### UC3: Review and approve suggestions

**Actor:** User
**Precondition:** Analysis completed (UC2)
**Primary flow (web UI):**

1. The web UI displays the analysis results in a sortable table
2. Each row shows: payee name, category, estimated amount (min–max), frequency,
   next due date, confidence score, source account (or a "varies" indicator when
   the pattern's transactions were withdrawn from more than one account, FR-30b)
3. High-confidence rows are pre-selected; others are unchecked
4. The user can edit amount, frequency, and start date inline per row
5. The user clicks "Create selected bills" to trigger UC4
6. The outcome of UC4 is shown inline (created / already exists / exists with different parameters / error)

**Alternative flow (terminal, `--auto-approve`):**

- All entries above the confidence threshold are approved without interaction
- Remaining entries are rejected or presented interactively row by row (y/n/a)
- Each printed suggestion includes the source account (or "varies") per FR-30b

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
2. Existing bills are checked before creation to avoid duplicates (FR-05a to FR-05d)
3. Created bills are logged

**Alternative flow:**

- Duplicate bill with identical amount range and frequency: application skips it and reports "already exists"
- Duplicate bill with differing amount range or frequency: application skips it and reports "exists with different parameters", including the differing values
- Firefly III rejects creation with a name-uniqueness validation error: application reports "already exists"

---

### UC5: Run in report mode (dry-run)

**Actor:** User
**Precondition:** Transaction history available
**Primary flow (web UI):**

1. The user enables the dry-run toggle in the UI before running the analysis
2. Analysis results and suggestions are displayed in the table as normal
3. The "Create selected bills" button is replaced by "Export"; nothing is written to Firefly III
4. The user can export suggestions as CSV or JSON via button
5. On completion, the UI shows a notification or download link naming the exported file (FR-31)

**Alternative flow (terminal):**

1. The application is run with the `--dry-run` flag
2. Analysis and suggestions are printed to the terminal
3. No bills are created in Firefly III
4. Suggestions are exported according to `EXPORT_FORMAT`
5. The application prints the path of the exported file (FR-31)

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

### UC8: Calibrate performance benchmark against real transaction data

**Actor:** Developer
**Precondition:** `FIREFLY_URL`/`FIREFLY_TOKEN` are configured (FR-10) and point
to a real Firefly III instance with transaction history
**Primary flow:**

1. Developer runs a dedicated, opt-in script against their own Firefly III
   instance
2. The script fetches the user's real withdrawal transactions for the
   configured lookback window (reusing `fetcher.fetch_transactions`)
3. The script runs `identify_recurring()` against the real dataset and
   measures elapsed time and transaction count, the same way TASK-009's
   synthetic benchmark does
4. The script reports the real transaction volume and elapsed time, for
   comparison against TASK-009's synthetic results, so NFR-05's provisional
   reference volume can be confirmed or revised against real-world data

**Notes:**

- Not part of `make test` or `make benchmark` (TASK-009's synthetic benchmark
  stays credential-free and CI-safe); this is a separate, manual, opt-in
  developer tool
- Read-only: it must not create, modify, or delete any data in Firefly III

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
| FR-05a | When the application is about to create a bill, the application shall verify whether a duplicate bill (see Definitions) already exists in Firefly III before creating the bill | UC4 |
| FR-05b | If a duplicate bill exists and its amount range and frequency equal the candidate's, then the application shall skip creation and report the outcome "already exists" | UC4 |
| FR-05c | If a duplicate bill exists and its amount range or frequency differs from the candidate's, then the application shall skip creation and report the outcome "exists with different parameters", including the differing values in the report | UC4 |
| FR-05d | If the Firefly III API rejects bill creation with a name-uniqueness validation error, then the application shall report the outcome "already exists" for that entry | UC4 |
| FR-06  | When the application creates a bill, the application shall compute the bill amount range (minimum and maximum) by applying the configured margin (`AMOUNT_MARGIN`) to the estimated amount | UC4 |
| FR-07a | When the application is started with the `--dry-run` flag or the `DRY_RUN` configuration parameter is set, the application shall activate dry-run mode | UC5 |
| FR-07b | While dry-run mode is active, the application shall not write any data to Firefly III | UC5 |
| FR-08  | Upon user request, the application shall export the analysis results to CSV format or JSON format | UC5 |
| FR-09  | The application shall log all API calls and their outcomes | UC1, UC4 |
| FR-10  | The application shall read its configuration from a `.env` file or from environment variables; when the same parameter is defined in both, environment variables shall take precedence | — |
| FR-11a | When a category include list is configured, the application shall include only transactions whose category matches the include list in the analysis | UC6 |
| FR-11b | When a category exclude list is configured, the application shall exclude transactions whose category matches the exclude list from the analysis | UC6 |
| FR-12  | When a transaction's category appears in the include list, the application shall increase that transaction's confidence score by the configured category confidence boost (`CATEGORY_CONFIDENCE_BOOST`) | UC6 |
| FR-13a | The web UI shall display the category name in the table view | UC6 |
| FR-13b | When a single category accounts for at least `CATEGORY_MAJORITY_THRESHOLD` of a payee's transactions, the application shall include that category name in the bill name; otherwise no category name is included. The share is computed over all of the payee's transactions, with uncategorized transactions counted as their own (non-matching) bucket | UC6 |
| FR-14  | The application shall process uncategorized transactions according to the configured behavior (`UNCATEGORIZED_BEHAVIOR`): under `include` and `neutral` the transaction is kept in the analysis unconditionally; under `exclude` the transaction is filtered out. Under `neutral` (see Definitions), the confidence score of the transaction's pattern is additionally reduced per FR-27 | UC6 |
| FR-15  | The application shall expose a web UI via a built-in HTTP server | UC3 |
| FR-16  | When the web UI page is loaded, the web UI shall fetch the existing categories from the Firefly III API and display them as multiselect lists | UC6 |
| FR-17a | When an analysis completes, the web UI shall display the analysis results in a sortable table | UC3 |
| FR-17b | The web UI shall accept inline edits of amount, frequency, and start date for each analysis result row | UC3 |
| FR-18  | When bill creation completes, the web UI shall display the outcome per bill (created, already exists, exists with different parameters, or error) without reloading the page | UC3 |
| FR-19  | When the user enables the dry-run toggle in the web UI, the web UI shall activate dry-run mode | UC5 |
| FR-20  | When the user clicks the export button in the web UI, the application shall export the analysis results to CSV format or JSON format | UC5 |
| FR-21  | The application shall cache categories, bills, transactions, and payees as JSON files on disk | UC7 |
| FR-22  | The application shall read a separate cache TTL from configuration for each cached data set (categories, bills, transactions, payees) | UC7 |
| FR-23  | When the application creates a new bill, the application shall invalidate the bills cache synchronously within the same creation operation, before the creation response is returned | UC7 |
| FR-24a | The web UI shall display a "Clear cache" button | UC7 |
| FR-24b | When the user clicks the "Clear cache" button, the application shall delete all cached data | UC7 |
| FR-25  | When the application is started in CLI mode with the `--clear-cache` flag, the application shall delete all cache files during startup, if a cache layer is implemented; otherwise the flag shall be a no-op that prints an informational "caching not implemented" message | UC7 |
| FR-26a | The `firefly-python-api` package shall read `FIREFLY_URL` and `FIREFLY_TOKEN` from environment variables or from a `.env` file; environment variables shall take precedence, per the same rule as FR-10 | — |
| FR-26b | The `firefly-python-api` package shall expose a `FireflyClient` class that provides a configured `requests.Session` | — |
| FR-27  | When the application classifies recurring payment patterns, the application shall compute the confidence score as 0.4 × occurrence score + 0.4 × regularity score + 0.2 × amount score + category boost − uncategorized penalty, and shall clamp the result to the range [0.0, 1.0], where uncategorized penalty equals `UNCATEGORIZED_CONFIDENCE_PENALTY` when the pattern's category is absent and `UNCATEGORIZED_BEHAVIOR` is `neutral`, else 0 | UC2 |
| FR-28  | Upon developer request, a dedicated opt-in script shall fetch the user's real withdrawal transactions from the configured Firefly III instance, run `identify_recurring()` against them, and report the real transaction count and elapsed time, without creating, modifying, or deleting any data in Firefly III | UC8 |
| FR-29  | The CLI `--help` output shall document the environment variables a user commonly needs to set per run mode, alongside the flags, so that configuration is discoverable without reading `.env.example`: `FIREFLY_URL` and `FIREFLY_TOKEN` (required), `DRY_RUN` (alternative to `--dry-run`), `EXPORT_FORMAT` (`csv`/`json`/`none`), `HIGH_CONFIDENCE_THRESHOLD` (auto-approve/review cutoff), `INCLUDE_CATEGORIES`/`EXCLUDE_CATEGORIES`, and `UNCATEGORIZED_BEHAVIOR` | UC3, UC5, UC6 |
| FR-30a | When the application identifies a recurring pattern (UC2), the application shall resolve a source account name for the pattern as the `source_name` value that occurs most frequently among the pattern's transactions, and shall additionally record whether more than one distinct `source_name` value occurs across the pattern's transactions | UC2 |
| FR-30b | The CLI review output (UC3) shall display, for each suggestion, the resolved source account name (FR-30a); when more than one distinct source account occurs in the pattern, the output shall display a "varies" indicator instead of a single account name | UC3 |
| FR-30c | The web UI table view (FR-17a) shall include a column showing the resolved source account name (FR-30a), or a "varies" indicator when more than one distinct source account occurs in the pattern | UC3 |
| FR-30d | The CSV and JSON export (FR-08) shall include the resolved source account name and the varies indicator (FR-30a) as fields of each exported pattern | UC5 |
| FR-31  | When an export (FR-08) completes, the application shall inform the user of the file path it wrote: in CLI mode via a printed message, and in the web UI (when implemented) via an on-page notification or download link | UC5 |
| FR-32a | Before computing occurrences, interval, and confidence (UC2 steps 3–6), the application shall split each payee/source-account subgroup (FR-32d) into amount clusters based on corroborated same-date co-occurrence: (a) group the subgroup's transactions by date and identify co-occurrence dates — dates with two or more transactions of differing amounts; (b) cluster the amounts observed at co-occurrence dates via a tolerance-based gap split (sort ascending, start a new candidate cluster whenever the gap to the previous amount exceeds `AMOUNT_CLUSTER_TOLERANCE` times the smaller of the two), and for each co-occurrence date record its signature — the set of candidate clusters its amounts fall into; (c) the split is corroborated only if some signature spanning two or more candidate clusters is shared by two or more distinct co-occurrence dates; if the subgroup has no co-occurrence date at all, or no signature is corroborated, the whole subgroup remains a single amount cluster regardless of amount variance across dates; (d) otherwise, assign every transaction in the subgroup — including those not on a co-occurrence date — to whichever candidate cluster's mean amount is numerically closest to its own amount. Each resulting cluster is processed as an independent recurring payment pattern candidate | UC2 |
| FR-32b | The application shall read the amount-cluster split tolerance from configuration (`AMOUNT_CLUSTER_TOLERANCE`, default `0.15`) | UC2 |
| FR-32c | When a payee produces more than one amount cluster (FR-32a) that each independently qualify as a recurring payment pattern, the application shall disambiguate the bill name of each resulting pattern by appending its representative (mean) amount to the name produced by FR-13b, so that FR-05a's name-only duplicate check does not conflate distinct clusters | UC2, UC4 |
| FR-32d | Before amount clustering (FR-32a), the application shall partition each payee group formed in UC2 step 1 by source account: transactions sharing the same `source_name` value form one subgroup, and transactions with no `source_name` form their own subgroup. FR-32a is then applied independently within each subgroup, so that transactions withdrawn through different accounts (e.g. a fixed transfer funding a spending account, versus that spending account's own purchases) are never amount-clustered together | UC2 |
| FR-33a | Within each payee/source-account/amount-cluster group (FR-32a, FR-32d), when two or more transactions share the exact same date, the application shall collapse them into a single billing event (see Definitions) whose amount is the sum of the collapsed transactions' amounts; occurrence count, median interval, and amount min/max/mean (UC2 steps 4–7) shall be computed over the resulting billing events rather than the pre-collapse transaction rows. Source account resolution (FR-30a) is unaffected and continues to be computed over the group's underlying transactions | UC2 |
| FR-34  | In CLI mode, while `fetcher.fetch_transactions()` is fetching transaction pages from Firefly III, the application shall display a progress bar showing pages fetched out of the total page count, driven by the `on_page` callback exposed by `firefly-python-api`'s `get_withdrawal_transactions()` (that package's REQ-008); when no callback support is available (e.g. an older `firefly-python-api` version), the application shall fall back to fetching without a progress bar rather than failing | UC1 |

---

## Non-functional Requirements

| ID      | Requirement | Trace |
| ------- | ----------- | ----- |
| NFR-01  | The application shall be written in Python 3.10+ | — |
| NFR-02  | The application shall use no external runtime dependencies other than `requests`, `python-dotenv`, `tqdm` (FR-34's CLI progress bar), and the selected web framework (`Flask` or `FastAPI`) **[FRAMEWORK TBD: select one; see Open Items]** | — |
| NFR-03  | When a Firefly III API response is paginated, the application shall fetch all pages and aggregate the results before returning them to the caller | UC1 |
| NFR-04  | If a common error (see Definitions) occurs, then the application shall display an error message that states the cause of the error, and shall not include a stack trace in the message | UC1 |
| NFR-05  | When the user starts an analysis of 24 months of transaction data (reference volume: **5,000** transactions — extrapolated from the owner's real transaction rate, 2,207 withdrawal transactions over ~16 months (2025-01-01 to 2026-05-05) per TASK-010's benchmark, scaled to a 24-month window (~3,300) with a 50% safety margin for slower/busier server conditions), the application shall complete the analysis within 60 seconds | UC2 |
| NFR-06  | The web UI shall load all of its assets from the local web server and shall not fetch any asset from an external CDN | UC3 |
| NFR-07a | The web server shall listen on the port configured via `WEB_PORT`, with a default port of 5000 | — |
| NFR-07b | The web server shall bind to the address configured via `WEB_HOST`, with a default bind address of `127.0.0.1`, including support for the value `0.0.0.0` | — |
| NFR-08  | *Reserved. Not used, retained to keep the ID sequence stable against version 0.1.0* | — |
| NFR-09  | The application shall retain the cache directory and its contents across application restarts | UC7 |
| NFR-10  | `firefly-python-api` shall be a standalone, pip-installable package shared with `firefly-bank-importer` | — |
| NFR-11  | The `firefly-python-api` package shall declare no runtime dependencies other than `requests` and `python-dotenv` | — |

---

## Error Messages

Example messages satisfying NFR-04 for each common error (see Definitions). These
are illustrative, not literal required strings — the binding obligation is that
the displayed message states the cause and contains no stack trace.

| Common error                                            | Example message                                                                                                     |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Unreachable Firefly III instance                        | `Cannot reach Firefly III at {FIREFLY_URL}: connection failed. Check network connectivity and FIREFLY_URL.`         |
| Invalid or expired API token                            | `Firefly III rejected the API token (401 Unauthorized). Check that FIREFLY_TOKEN is valid and has not expired.`     |
| Invalid or missing required configuration value         | `Missing required configuration value: {parameter_name}. Set it in .env or as an environment variable.`             |
| Insufficient API token permissions                      | `Firefly III rejected the request (403 Forbidden). The API token may lack the permission required to create bills.` |
| Firefly III API error response (see Definitions)        | `Firefly III returned an error (HTTP {status_code}) while {operation}: {firefly_message}.`                          |
| Cache directory not writable                            | `Cannot write to cache directory {CACHE_DIR}: {reason}. Check permissions or free disk space.`                      |

Note: a name-uniqueness rejection at bill creation is not a common error; it is mapped to the outcome "already exists" per FR-05d.

---

## Scope Exclusions

Binding negative requirements defining the boundary of version 1.0. These are intentional exclusions and shall be verified as such.

| ID    | Requirement |
| ----- | ----------- |
| SE-01 | The application shall not create categories or budgets in Firefly III |
| SE-02 | The application shall not create a bill for an entry whose confidence score is below the configured confidence threshold, unless the user explicitly approves the entry |
| SE-03 | The application shall not delete or update existing bills in Firefly III |

Note on SE-02: version 0.1.0 equated "irregular pattern" with "confidence below threshold". These are distinct concepts (frequency is interval-based per FR-03; confidence is score-based per FR-27). SE-02 is expressed in terms of confidence, which matches the approval logic in UC3.

Note on SE-03 and FR-05c: the outcome "exists with different parameters" surfaces amount and frequency drift to the user but does not update the existing bill; updating remains excluded per SE-03.

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

| Parameter                          | Description                                                              | Default         |
| ---------------------------------- | ------------------------------------------------------------------------ | --------------- |
| `FIREFLY_URL`                      | Base URL of the Firefly III instance                                     | *(required)*    |
| `FIREFLY_TOKEN`                    | Personal Access Token                                                    | *(required)*    |
| `LOOKBACK_MONTHS`                  | Months of transaction history to analyze                                 | `24`            |
| `MIN_OCCURRENCES`                  | Minimum occurrences to classify as recurring                             | `2`             |
| `AMOUNT_MARGIN`                    | Margin for min/max amount (fraction)                                     | `0.10`          |
| `AMOUNT_CLUSTER_TOLERANCE`         | Relative amount gap that starts a new cluster within a payee (FR-32a)    | `0.15`          |
| `HIGH_CONFIDENCE_THRESHOLD`        | Confidence threshold for auto-approval in CLI mode                       | `0.80`          |
| `DRY_RUN`                          | Do not create any bills                                                  | `false`         |
| `EXPORT_FORMAT`                    | Export format (csv/json/none)                                            | `none`          |
| `INCLUDE_CATEGORIES`               | Comma-separated category include list                                    | *(empty = all)* |
| `EXCLUDE_CATEGORIES`               | Comma-separated category exclude list                                    | *(empty)*       |
| `CATEGORY_CONFIDENCE_BOOST`        | Confidence boost for transactions matching the include list              | `0.15`          |
| `CATEGORY_MAJORITY_THRESHOLD`      | Min. share of a payee's transactions in one category to name it (FR-13b) | `0.80`          |
| `UNCATEGORIZED_BEHAVIOR`           | Handling of uncategorized transactions (include/exclude/neutral)         | `neutral`       |
| `UNCATEGORIZED_CONFIDENCE_PENALTY` | Confidence penalty for neutral uncategorized patterns (FR-27)            | `0.10`          |
| `WEB_PORT`                         | Port the web server listens on                                           | `5000`          |
| `WEB_HOST`                         | IP address the web server binds to                                       | `127.0.0.1`     |
| `CACHE_DIR`                        | Directory for cache files                                                | `./cache`       |
| `CACHE_TTL_CATEGORIES`             | TTL for category cache (seconds)                                         | `86400`         |
| `CACHE_TTL_BILLS`                  | TTL for bills cache (seconds)                                            | `3600`          |
| `CACHE_TTL_TRANSACTIONS`           | TTL for transaction cache (seconds)                                      | `3600`          |
| `CACHE_TTL_PAYEES`                 | TTL for payee cache (seconds)                                            | `86400`         |

---

## Open Items

Decisions required from the requirement owner before this specification is baselined.

| # | Item | Affected requirements |
| --- | ---- | --------------------- |
| 5 | Web framework selection: Flask or FastAPI — **deferred**: no task through TASK-009 touches `app.py` or a web framework, so this costs nothing to postpone. Open question behind it: is a web UI needed at all, given `--dry-run` + `EXPORT_FORMAT=csv` already covers category filtering (`.env`), cache clearing (`--clear-cache`), and reviewing suggestions in a spreadsheet? The concrete gap if the web UI is dropped is FR-17b's inline edit + an import-edited-CSV-back-into-the-app path, which is unspecified today. Revisit after the CLI (through TASK-009) has been used in practice | NFR-02 |
| 8 | **Further resolved (2026-07-11):** TASK-007 (cache layer) is un-deferred for its CLI-relevant scope. New motivation, independent of the web UI: fetching real transaction history from a remote Firefly III instance is slow enough (dozens of paginated requests) that re-fetching on every local development/test run against real data is a real cost; caching transactions and bills to disk removes that cost for repeated `--dry-run` runs during development. FR-21 (transactions + bills subsets), FR-22 (their two TTLs), FR-23, FR-25, and NFR-09 are therefore active requirements for the terminal-only MVP, implemented by TASK-007. FR-21's remaining two data sets (categories, payees) remain deferred — they are only consumed via the `/api/categories` web endpoint, which does not exist without a web UI. FR-24a/FR-24b (the web UI's "Clear cache" button) and NFR-06 (no external CDN) remain deferred for the same reason, contingent on Open Item #5 | FR-21, FR-22, FR-23, FR-24a, FR-24b, FR-25, NFR-06, NFR-09 |

---

## Changelog

### 0.2.17 (2026-07-11)

- Revised FR-32a and added FR-32d to fix over-fragmentation of payees whose
  transactions genuinely span more than one financial role, found during
  owner review of a real analysis report generated after TASK-012. Two
  distinct issues were identified for payee "ICA":
  - Its transactions came from two different source accounts — a fixed
    monthly transfer from `SEB Räkningskonto` funding a dedicated spending
    account, and the actual day-to-day grocery purchases withdrawn from
    `ICA-banken Matkonto`. FR-32d now partitions each payee group by source
    account *before* amount clustering (FR-32a runs independently per
    subgroup), so a funding transfer and the spending it funds are never
    amount-clustered together.
  - Even within the `ICA-banken Matkonto` subgroup alone, occasional
    same-day double purchases (differing amounts) were enough to trigger
    FR-32a's old tolerance-based split; because grocery amounts are
    continuously distributed and almost never repeat exactly, the
    tolerance-gap chained across the full amount range and fragmented the
    subgroup into over a dozen low-confidence sub-clusters — the same
    failure mode the 0.2.15 EON fix addressed, but reachable even without
    the payee's overall variance being the trigger. FR-32a now additionally
    requires the split to be *corroborated*: a candidate multi-cluster
    signature (which candidate clusters a co-occurrence date's amounts fall
    into) must recur on at least two distinct co-occurrence dates before
    the subgroup is split. A single day's coincidental double purchase no
    longer fragments an otherwise continuously variable spending pattern,
    while payees that genuinely bundle repeating parallel charges (e.g.
    "Apple"'s co-occurring subscriptions) still split as before.
  - Owner-confirmed side effect of FR-32d: since a resulting pattern's
    transactions now share a single source account by construction (having
    already been partitioned on it), FR-30a's `source_account_varies` flag
    no longer occurs in the normal case — there is nothing left to vary
    within a pattern. FR-30a/b/c/d remain correct as specified (the "varies"
    computation and display are unchanged), but are expected to report
    `False`/no-"varies" for essentially all patterns going forward.

### 0.2.16 (2026-07-11)

- Further resolved Open Item #8: un-deferred TASK-007 (cache layer) for its
  CLI-relevant scope (transactions and bills caching, FR-21/22/23/25/NFR-09).
  New motivation, independent of the web UI: repeated local development/test
  runs against a real Firefly III instance re-fetch the same paginated
  transaction history every time, which is slow enough to be a real
  development cost; a TTL-aware disk cache removes it for repeated `--dry-run`
  runs. Categories/payees caching (the rest of FR-21) and the web UI's "Clear
  cache" button (FR-24a/b) remain deferred, contingent on Open Item #5 (no
  web UI exists yet to consume them).

### 0.2.15 (2026-07-11)

- Revised FR-32a: amount clustering is now based on same-date co-occurrence of
  differing amounts, not on amount variance alone. Verified against real
  transaction data during owner review: "EON" (a monthly electricity bill
  whose amount legitimately fluctuates 661–4426 kr by season and
  consumption, never two transactions on the same date) was being
  fragmented into several weak, low-confidence sub-clusters by the
  original amount-gap-only clustering (FR-32a as added in 0.2.14) — the
  same tolerance-based split that correctly separates "Apple"'s two
  co-occurring subscriptions couldn't tell a genuinely variable single
  bill from a payee that bundles multiple simultaneous charges. Under the
  revised rule, a payee is only split when it has at least one date with
  two differing amounts (revealing real parallel sub-charges); such a
  payee's remaining transactions are then assigned to whichever cluster's
  mean is numerically closest, rather than by amount-gap alone. A payee
  with no co-occurrence date (like EON) is never split, restoring it to a
  single high-confidence monthly pattern.

### 0.2.14 (2026-07-11)

- Added FR-34 and a `tqdm` runtime dependency (NFR-02): in CLI mode, fetching
  transactions (UC1) now shows a progress bar of pages fetched out of the
  total, driven by a per-page `on_page` callback that `firefly-python-api`
  will expose per that package's REQ-008 (its TASK-011, not yet
  implemented/synced into `lib/firefly-python-api` at time of writing — this
  requirement is blocked on that dependency landing, same pattern as
  TASK-002's dependency on that package's TASK-005). If the vendored
  `firefly-python-api` does not yet support `on_page`, the application falls
  back to fetching without a progress bar rather than failing, so this
  requirement can be merged ahead of the dependency without breaking
  existing behavior. Intent: fetching 24 months of transactions from a
  remote Firefly III instance can take long enough that, without visible
  progress, the CLI looks hung.

### 0.2.13 (2026-07-11)

- Added FR-32a/b/c and the "Amount cluster" definition: within a payee group,
  transactions are now further split into amount clusters (tolerance
  `AMOUNT_CLUSTER_TOLERANCE`, default 0.15) before frequency/confidence are
  computed, and each cluster is disambiguated in the bill name by its
  representative amount. Intent: a single `destination_name` sometimes hides
  more than one genuinely distinct recurring charge (e.g. several
  subscriptions billed through one merchant with different amounts); today
  these get flattened into one noisy group whose interval/amount variance
  sinks its confidence score and frequency classification (observed for real
  payees analyzed during owner review: "Media och Streaming", "Apple").
  Splitting by amount lets each real recurring charge be classified on its
  own merits instead of being drowned out by its siblings.
- Added FR-33a and the "Billing event" definition: within a payee/amount-
  cluster group, transactions sharing the exact same date are now collapsed
  into a single billing event whose amount is their sum, before occurrence
  count, median interval, and amount statistics are computed. Intent: some
  recurring charges are booked as more than one same-day, same-amount
  transaction (observed for "Skandinaviska Enskilda Banken": the same monthly
  fee billed twice on the same day, once per household member's account).
  Treated as two independent transactions, every other interval collapses to
  0 days, which sank the median interval to 0 and misclassified an otherwise
  clean monthly pattern as irregular. Budget-wise the two payments are one
  combined outflow, so they are now summed into a single billing event per
  date before the interval and amount statistics are computed.

### 0.2.12 (2026-07-11)

- Added FR-30a/b/c/d: each recurring pattern now resolves the source account it
  is most often paid from (or a "varies" indicator when the payee was paid from
  more than one account), shown in the CLI review output, in the web UI table
  view (once built), and included in CSV/JSON export. Intent: let the user
  balance funds between accounts ahead of bill payment, since bills are
  otherwise silently attributed only to a payee, not to the account the money
  actually leaves from.
- Added FR-31: on export completion, the application must tell the user where
  the file went — a printed path in CLI mode, a notification/download link in
  the web UI once built — instead of silently writing a file the user has to
  guess the location of.

### 0.2.11 (2026-07-11)

- Added FR-29: `--help` must document the environment variables a user needs for
  different run modes (required credentials, dry-run, export format, confidence
  threshold, category filters), not just the CLI flags — surfaced during TASK-005
  usage as a usability gap (running the CLI required cross-referencing
  `.env.example` separately).

### 0.2.10 (2026-07-11)

- Open Item #8 partially resolved: caching (TASK-007, FR-21/22/23/FR-24a/FR-24b/NFR-09)
  is deprioritized/skipped for the terminal-only MVP, since it was motivated by
  web UI polling and the web UI is already deferred (Open Item #5). FR-25
  amended so `--clear-cache` is a no-op with an informational message when no
  cache layer is implemented, rather than a hard failure. Clears the way for
  TASK-005 (CLI orchestration) to proceed without TASK-007.

### 0.2.9 (2026-07-11)

- Open Item #9 resolved: TASK-010's benchmark (`scripts/benchmark_real_data.py`,
  run via `make benchmark-real`) ran `identify_recurring()` against the
  requirement owner's real Firefly III transaction history — 2,207
  withdrawal transactions spanning ~16 months (2025-01-01 to 2026-05-05, less
  than the full 24-month lookback window) — completing in ~0.012s. Scaling
  the measured rate (~4.5 transactions/day) to a 24-month window gives
  ~3,300 transactions; with a 50% safety margin for slower or busier server
  conditions, NFR-05's reference volume is now **5,000** transactions,
  replacing the provisional 20,000 figure carried over from TASK-009's
  synthetic-only benchmark. No longer provisional.

### 0.2.8 (2026-07-11)

- Added UC8 and FR-28: a new, opt-in, credential-requiring developer script
  (planned as TASK-010) will run the same recurring-payment analysis against
  a developer's real Firefly III transaction history to calibrate NFR-05's
  reference volume, which TASK-009 could only establish from synthetic data.
  Read-only — never creates, modifies, or deletes Firefly III data. Added
  Open Item #9 to track this.

### 0.2.7 (2026-07-11)

- Open Item #6 resolved: TASK-009's benchmark (`tests/benchmark_analyzer.py`,
  run via `make benchmark`) measured `identify_recurring()` elapsed time
  across synthetic 24-month datasets of 500, 2,000, 5,000, 10,000, and 20,000
  transactions (a 70/30 mix of recurring payees and non-recurring noise). The
  largest size, 20,000 transactions, completed in ~0.10s — far under the
  60-second bound. NFR-05's `[VALUE TBD]` is now **20,000**, framed as a
  provisional reference volume pending confirmation against real user data;
  the current headroom suggests the bound itself may be worth revisiting once
  real-world volumes are known.

### 0.2.6 (2026-07-11)

- Open Item #7 resolved: FR-13b now uses majority/mode-based tolerance instead
  of a strict "exactly one distinct category" reading. A category is included
  in the bill name when it accounts for at least `CATEGORY_MAJORITY_THRESHOLD`
  (default `0.80`) of a payee's transactions, tolerating a small number of
  miscategorized outliers rather than discarding the category name entirely.
  New configuration parameter `CATEGORY_MAJORITY_THRESHOLD` added, consistent
  with the other configurable thresholds (`AMOUNT_MARGIN`,
  `HIGH_CONFIDENCE_THRESHOLD`, `CATEGORY_CONFIDENCE_BOOST`).

### 0.2.5 (2026-07-09)

- Open Item #1 revised: the duplicate bill definition (Definitions) is now a
name match only, compared case-sensitively after trimming leading and
trailing whitespace; amount and frequency are no longer part of the
criterion. Rationale: amounts are recalculated from transaction history at
every run, so an exact amount match fails on re-runs for the very bills
FR-05 exists to skip, and Firefly III enforces per-user unique bill names
("unique_object_for_user"), turning such misses into 422 errors instead of
skips. Case-sensitive comparison is chosen because candidate names come
from Firefly's own `destination_name` values.
- FR-05 decomposed into FR-05a (pre-creation duplicate check), FR-05b (skip
and report "already exists" on identical parameters), FR-05c (skip and
report "exists with different parameters" on differing amount range or
frequency, surfacing the differing values), and FR-05d (map a
name-uniqueness rejection from the Firefly III API to the outcome
"already exists" as a safety net for collation differences).
- FR-18, UC3 step 6, and UC4's alternative flows updated with the new outcome
"exists with different parameters". Note added under Scope Exclusions
clarifying that FR-05c reports drift without updating bills (SE-03).
- Common error definition adjusted: the generic Firefly III API error entry
now explicitly excludes 401, 403, and the name-uniqueness rejection handled
per FR-05d, removing the overlap with the dedicated 403 entry and the
conflict with FR-05d's outcome mapping. Clarifying note added in Error
Messages.

### 0.2.4 (2026-07-09)

- Open Item #2 resolved: `neutral` uncategorized behavior no longer filters
transactions differently from `include` — both always keep uncategorized
transactions in the analysis. Instead, `neutral` reduces the pattern's
confidence score via a new `UNCATEGORIZED_CONFIDENCE_PENALTY` term in the
FR-27 formula (default `0.10`), reusing the existing confidence/review
mechanism (UC3, SE-02) rather than introducing a second, filtering-based
exclusion path that could silently drop real recurring bills from the
analysis. FR-14, FR-27, UC2, and the Definitions and Configuration
Parameters tables updated accordingly.

### 0.2.3 (2026-07-09)

- Open Item #3 resolved: the "common error" list (Definitions, NFR-04) is now
enumerated as six errors — unreachable instance, invalid/expired token,
invalid/missing required config, insufficient token permissions, other
Firefly III API error responses, and unwritable cache directory — with an
example message per error in a new Error Messages section.

### 0.2.2 (2026-07-09)

- Open Item #1 resolved: a duplicate bill (Definitions, FR-05) is now defined as
a name match (case-insensitive) plus an exact match on `amount_min`,
`amount_max`, and `repeat_freq` — not name alone. Chosen over an overlapping-
amount-range match for determinism and testability. *(Superseded by 0.2.5.)*

### 0.2.1 (2026-07-09)

- Open Item #4 resolved: environment variables take precedence over `.env` file
values when the same parameter is defined in both (FR-10, FR-26a). Rationale:
matches `python-dotenv`'s default behavior and the 12-factor-app convention;
one-off test overrides remain trivial via a shell-prefixed variable
(`VAR=value command`) without editing `.env`.

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
