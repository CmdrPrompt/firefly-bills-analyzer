"""Standalone performance benchmark for ``analyzer.identify_recurring`` (NFR-05).

Not a pytest test — the filename doesn't match ``test_*.py`` so it is excluded
from `make test` and its coverage. Run explicitly via `make benchmark`.
"""

from __future__ import annotations

import itertools
import json
import random
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.analyzer import identify_recurring
from firefly_bills_analyzer.config import Config

DATASET_SIZES = [500, 2_000, 5_000, 10_000, 20_000]
WINDOW_START = date(2024, 1, 1)
WINDOW_DAYS = 24 * 30
CATEGORIES = ["Streaming", "Utilities", "Insurance", "Groceries", None]
NFR_05_BOUND_SECONDS = 60.0
RESULTS_PATH = Path(__file__).resolve().parent.parent / "benchmark_results.json"

# (frequency label, interval in days, occurrences across a 24-month window)
_PATTERNS: list[tuple[str, int, int]] = [
    ("monthly", 30, 24),
    ("quarterly", 91, 8),
    ("yearly", 365, 2),
]


def _make_config() -> Config:
    return Config(
        firefly_url="https://firefly.example.com",
        firefly_token="tok",
        lookback_months=24,
        min_occurrences=2,
        amount_margin=0.10,
        amount_cluster_tolerance=0.15,
        high_confidence_threshold=0.80,
        category_confidence_boost=0.15,
        category_majority_threshold=0.80,
        uncategorized_confidence_penalty=0.10,
        uncategorized_behavior="neutral",
        include_categories=[],
        exclude_categories=[],
        dry_run=False,
        export_format="none",
        web_port=5000,
        web_host="127.0.0.1",
        cache_dir="./cache",
        cache_ttl_categories=86400,
        cache_ttl_bills=3600,
        cache_ttl_transactions=3600,
        cache_ttl_payees=86400,
    )


def _recurring_transactions(
    rng: random.Random,
    payee_index: int,
    frequency: str,
    interval_days: int,
    occurrences: int,
) -> list[TransactionRead]:
    base_amount = rng.uniform(5.0, 200.0)
    category = rng.choice(CATEGORIES)
    payee = f"{frequency.capitalize()} Payee {payee_index}"
    transactions = []
    for occurrence in range(occurrences):
        jitter_days = rng.randint(-2, 2)
        txn_date = WINDOW_START + timedelta(days=occurrence * interval_days + jitter_days)
        amount = base_amount * rng.uniform(0.97, 1.03)
        transactions.append(
            TransactionRead(
                date=txn_date.isoformat(),
                amount=f"{amount:.2f}",
                destination_name=payee,
                category_name=category,
            )
        )
    return transactions


def _noise_transaction(rng: random.Random, index: int) -> TransactionRead:
    txn_date = WINDOW_START + timedelta(days=rng.randint(0, WINDOW_DAYS))
    return TransactionRead(
        date=txn_date.isoformat(),
        amount=f"{rng.uniform(1.0, 500.0):.2f}",
        destination_name=f"Noise Payee {index}",
        category_name=rng.choice(CATEGORIES),
    )


def generate_dataset(size: int, seed: int = 42) -> list[TransactionRead]:
    """Build a synthetic 24-month dataset of ``size`` transactions.

    ~70% of transactions belong to recurring payees split evenly across
    monthly/quarterly/yearly patterns; the remainder are single-occurrence
    noise payees that should never be classified as recurring.
    """
    rng = random.Random(seed)
    transactions: list[TransactionRead] = []
    pattern_cycle = itertools.cycle(_PATTERNS)
    payee_index = 0
    noise_index = 0
    recurring_target = int(size * 0.7)

    while len(transactions) < recurring_target:
        frequency, interval_days, occurrences = next(pattern_cycle)
        remaining = recurring_target - len(transactions)
        group = _recurring_transactions(rng, payee_index, frequency, interval_days, occurrences)
        transactions.extend(group[:remaining])
        payee_index += 1

    while len(transactions) < size:
        transactions.append(_noise_transaction(rng, noise_index))
        noise_index += 1

    rng.shuffle(transactions)
    return transactions


@dataclass(frozen=True)
class BenchmarkResult:
    transaction_count: int
    elapsed_seconds: float


def run_benchmark(sizes: list[int] = DATASET_SIZES) -> list[BenchmarkResult]:
    config = _make_config()
    results = []
    for size in sizes:
        dataset = generate_dataset(size)
        started = time.perf_counter()
        identify_recurring(dataset, config)
        elapsed = time.perf_counter() - started
        results.append(BenchmarkResult(transaction_count=size, elapsed_seconds=elapsed))
    return results


def _print_table(results: list[BenchmarkResult]) -> None:
    print(f"{'Transactions':>14} | {'Elapsed (s)':>12}")
    print("-" * 29)
    for result in results:
        print(f"{result.transaction_count:>14} | {result.elapsed_seconds:>12.3f}")


def _write_results(results: list[BenchmarkResult]) -> None:
    payload = [
        {"transaction_count": r.transaction_count, "elapsed_seconds": r.elapsed_seconds}
        for r in results
    ]
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    results = run_benchmark()
    _print_table(results)
    _write_results(results)

    largest = results[-1]
    assert largest.elapsed_seconds < NFR_05_BOUND_SECONDS, (
        f"NFR-05 regression: {largest.transaction_count} transactions took "
        f"{largest.elapsed_seconds:.2f}s (bound: {NFR_05_BOUND_SECONDS}s)"
    )
    print(
        f"\nOK: {largest.transaction_count} transactions completed in "
        f"{largest.elapsed_seconds:.2f}s (< {NFR_05_BOUND_SECONDS}s bound)"
    )


if __name__ == "__main__":
    main()
