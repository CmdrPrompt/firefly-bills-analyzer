"""Opt-in developer script: calibrate NFR-05's reference volume against a
real Firefly III instance (UC8, FR-28).

Read-only — fetches transactions and runs the analysis, but never creates,
modifies, or deletes anything in Firefly III (no `bills_creator` import).
Requires FIREFLY_URL/FIREFLY_TOKEN configured via `.env` or environment
variables (FR-10). Not part of `make test` or `make benchmark` — run via
`make benchmark-real`.
"""

from __future__ import annotations

import time

from firefly_bills_analyzer.analyzer import identify_recurring
from firefly_bills_analyzer.config import Config, ConfigError
from firefly_bills_analyzer.fetcher import fetch_transactions


def main() -> None:
    try:
        config = Config.from_env()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    print(f"Fetching real withdrawal transactions from {config.firefly_url} ...")
    fetch_started = time.perf_counter()
    transactions = fetch_transactions(config)
    fetch_elapsed = time.perf_counter() - fetch_started

    analysis_started = time.perf_counter()
    identify_recurring(transactions, config)
    analysis_elapsed = time.perf_counter() - analysis_started

    print(f"Fetched {len(transactions)} transaction(s) in {fetch_elapsed:.3f}s")
    print(f"identify_recurring() took {analysis_elapsed:.3f}s")
    print(
        f"\nReal transaction count: {len(transactions)}\n"
        f"Analysis elapsed: {analysis_elapsed:.3f}s\n"
        "Compare against tests/benchmark_analyzer.py's synthetic results to "
        "confirm or revise NFR-05's reference volume."
    )


if __name__ == "__main__":
    main()
