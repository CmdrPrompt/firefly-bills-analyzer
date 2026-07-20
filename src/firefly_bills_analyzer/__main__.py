"""Entry point: python -m firefly_bills_analyzer.

Wires the full pipeline together (UC1 -> UC6 -> UC2 -> UC3 -> UC4/UC5):
fetch transactions, filter by category, identify recurring patterns, review
and approve suggestions, then create bills or report them in dry-run mode.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from firefly_python_api import FireflyClient

from firefly_bills_analyzer import (
    account_filter,
    analyzer,
    bills_creator,
    cache,
    category_filter,
    exporter,
    fetcher,
)
from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.config import Config, ConfigError

_EXPORT_EXTENSIONS = {"csv": "csv", "json": "json"}


_ENV_VARS_HELP = """\
Key environment variables (set in a .env file or the shell; see .env.example
for the full list):
  FIREFLY_URL, FIREFLY_TOKEN     required: your Firefly III instance and API token
  DRY_RUN                        true/false, alternative to --dry-run
  EXPORT_FORMAT                  csv, json, or none (default)
  HIGH_CONFIDENCE_THRESHOLD      confidence cutoff for auto-approval, 0.0-1.0 (default 0.80)
  INCLUDE_CATEGORIES             comma-separated categories to include (UC6)
  EXCLUDE_CATEGORIES             comma-separated categories to exclude (UC6)
  UNCATEGORIZED_BEHAVIOR         include, exclude, or neutral (default)
"""


class _HelpFormatter(argparse.HelpFormatter):
    """Wraps the description normally but leaves the env-var epilog untouched."""

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        if text == _ENV_VARS_HELP:
            return "".join(indent + line for line in text.splitlines(keepends=True))
        return super()._fill_text(text, width, indent)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="firefly-bills-analyzer",
        description=(
            "Identify recurring payments in your Firefly III transaction history "
            "and create matching bills (subscriptions)."
        ),
        epilog=_ENV_VARS_HELP,
        formatter_class=_HelpFormatter,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="report suggested bills without writing anything to Firefly III",
    )
    p.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="approve every suggestion at or above HIGH_CONFIDENCE_THRESHOLD without prompting",
    )
    p.add_argument(
        "--clear-cache",
        action="store_true",
        default=False,
        help="delete cached transactions/bills data before running",
    )
    return p


def _format_suggestion(pattern: RecurringPattern) -> str:
    category = f" [{pattern.category_name}]" if pattern.category_name else ""
    if pattern.source_account_varies:
        source_account = " from (varies)"
    elif pattern.source_account_name is not None:
        source_account = f" from {pattern.source_account_name}"
    else:
        source_account = ""
    return (
        f"{pattern.destination_name}{category}{source_account}: {pattern.frequency}, "
        f"{pattern.amount_min:.2f}-{pattern.amount_max:.2f} "
        f"(confidence {pattern.confidence:.0%}, {pattern.occurrences} occurrences)"
    )


def _review(
    patterns: list[RecurringPattern], config: Config, *, auto_approve: bool
) -> list[RecurringPattern]:
    """Approve entries per UC3. Returns the approved subset, in input order."""
    if auto_approve:
        auto_approved = [p for p in patterns if p.confidence >= config.high_confidence_threshold]
        approved_ids = {id(p) for p in auto_approved}
        for pattern in patterns:
            status = "approved" if id(pattern) in approved_ids else "skipped (below threshold)"
            print(f"[auto] {status}: {_format_suggestion(pattern)}")
        return auto_approved

    approved: list[RecurringPattern] = []
    approve_all = False
    for pattern in patterns:
        print(_format_suggestion(pattern))
        if approve_all:
            approved.append(pattern)
            continue
        answer = input("Create this bill? [y]es / [n]o / [a]ll / [q]uit: ").strip().lower()
        if answer == "a":
            approve_all = True
            approved.append(pattern)
        elif answer == "y":
            approved.append(pattern)
        elif answer == "q":
            break
        # Any other answer, including "n" or an empty Enter, rejects the entry.
    return approved


def _print_outcomes(outcomes: list[bills_creator.BillOutcome]) -> None:
    for outcome in outcomes:
        print(f"[{outcome.status}] {outcome.name}: {outcome.message}")


def _default_export_path(fmt: str) -> str:
    ext = _EXPORT_EXTENSIONS[fmt]
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"./firefly-bills-{timestamp}.{ext}"


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if args.clear_cache:
        cache.clear_all(Path(config.cache_dir))
        print(f"Cleared cache directory: {config.cache_dir}")

    dry_run = args.dry_run or config.dry_run

    transactions = fetcher.fetch_transactions(config)
    transactions = category_filter.filter_transactions(transactions, config)
    transactions = account_filter.filter_transactions(transactions, config)
    patterns = analyzer.identify_recurring(transactions, config)

    approved: list[RecurringPattern] = []
    if not patterns:
        print("No recurring payment patterns found.")
    else:
        approved = _review(patterns, config, auto_approve=args.auto_approve)

    if approved:
        client = FireflyClient(config.firefly_url, config.firefly_token)
        outcomes = bills_creator.create_bills(approved, client, config, dry_run=dry_run)
        _print_outcomes(outcomes)
    elif patterns:
        print("No entries approved; no bills created.")

    if config.export_format != "none":
        path = _default_export_path(config.export_format)
        exporter.export(patterns, config.export_format, path)
        print(f"Exported {len(patterns)} pattern(s) to {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
