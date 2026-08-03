"""Entry point: python -m firefly_bills_analyzer.

Wires the full pipeline together (UC1 -> UC6 -> UC2 -> UC3 -> UC4/UC5):
fetch transactions, filter by category, identify recurring patterns, review
and approve suggestions, then create bills or report them in dry-run mode.
"""

from __future__ import annotations

import argparse
import logging
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
    household_spend,
    income,
    payee_filter,
)
from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.config import Config, ConfigError
from firefly_bills_analyzer.household_spend import HouseholdSpendResult
from firefly_bills_analyzer.income import IncomeResult

logger = logging.getLogger(__name__)

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
        # FR-30e: under FR-32d's partitioning this cannot occur normally;
        # reaching here means the partitioning invariant has been violated.
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


def _format_income_source(source: income.IncomeSource) -> str:
    return (
        f"{source.income_account}: {source.payer} "
        f"{source.observed_net_income:.2f} observed {source.observed_date} "
        f"({source.occurrences} occurrences)"
    )


def _format_income_issue(issue: income.IncomeAccountIssue) -> str:
    candidates = ", ".join(candidate.payer for candidate in issue.candidates)
    return f"{issue.income_account}: {issue.reason} (candidates: {candidates})"


def _print_income(result: IncomeResult) -> None:
    """FR-46: display income sources and issue accounts before the review flow."""
    for source in result.sources:
        print(f"[income] {_format_income_source(source)}")
    for issue in result.issues:
        print(f"[income] {_format_income_issue(issue)}")


def _format_household_spend_record(record: household_spend.HouseholdSpendRecord) -> str:
    category = f" [{record.category}]" if record.category else ""
    account = f" from {record.source_account}" if record.source_account else ""
    if record.median is None:
        return (
            f"{record.source_account}{category}{account}: only {record.month_count} "
            "complete month(s), no median yet"
        )
    return (
        f"{record.source_account}{category}{account}: median {record.median:.2f}/mo "
        f"(mean {record.mean:.2f}, range {record.minimum:.2f}-{record.maximum:.2f}, "
        f"{record.month_count} complete month(s))"
    )


def _format_one_off_purchase(purchase: household_spend.OneOffPurchase) -> str:
    category = f" [{purchase.category}]" if purchase.category else ""
    account = f" from {purchase.source_account}" if purchase.source_account else ""
    return (
        f"{purchase.date} {purchase.payee}{category}{account}: {purchase.amount:.2f} "
        f"(threshold {purchase.threshold:.2f})"
    )


def _print_household_spend(result: HouseholdSpendResult) -> None:
    """FR-52: display household spend figures, one-off purchases, and
    anything reported under FR-49e or FR-50, before the review flow."""
    for record in result.records:
        print(f"[household-spend] {_format_household_spend_record(record)}")
    for purchase in result.one_off_purchases:
        print(f"[household-spend] one-off: {_format_one_off_purchase(purchase)}")
    for category in result.unmatched_categories:
        print(f"[household-spend] unmatched category: {category}")
    for category in result.unmatched_threshold_overrides:
        print(f"[household-spend] unmatched threshold override: {category}")
    if result.include_tag_count or result.exclude_tag_count:
        print(
            f"[household-spend] tag corrections: {result.include_tag_count} included, "
            f"{result.exclude_tag_count} excluded"
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


def _default_income_export_path(fmt: str) -> str:
    ext = _EXPORT_EXTENSIONS[fmt]
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"./firefly-income-{timestamp}.{ext}"


def _default_household_spend_export_path(fmt: str) -> str:
    ext = _EXPORT_EXTENSIONS[fmt]
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"./firefly-household-spend-{timestamp}.{ext}"


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

    raw_transactions = fetcher.fetch_transactions(config)
    deposits = fetcher.fetch_deposits(config)
    logger.debug("fetch_deposits() returned %d deposit(s)", len(deposits))
    transactions = category_filter.filter_transactions(raw_transactions, config)
    transactions = account_filter.filter_transactions(transactions, config)
    transactions = payee_filter.filter_transactions(transactions, config)
    patterns = analyzer.identify_recurring(transactions, config)

    income_result = income.detect_income(deposits, config)
    _print_income(income_result)

    household_spend_result = household_spend.aggregate_household_spend(raw_transactions, config)
    _print_household_spend(household_spend_result)

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

    income_detection_enabled = bool(income_result.sources or income_result.issues)
    if income_detection_enabled and config.export_format != "none":
        income_path = _default_income_export_path(config.export_format)
        exporter.export_income(
            income_result.sources, income_result.issues, config.export_format, income_path
        )
        print(f"Exported {len(income_result.sources)} income source(s) to {income_path}")

    household_spend_enabled = bool(
        household_spend_result.records
        or household_spend_result.one_off_purchases
        or household_spend_result.unmatched_categories
        or household_spend_result.unmatched_threshold_overrides
        or household_spend_result.include_tag_count
        or household_spend_result.exclude_tag_count
    )
    if household_spend_enabled and config.export_format != "none":
        household_spend_path = _default_household_spend_export_path(config.export_format)
        exporter.export_household_spend(
            household_spend_result, config.export_format, household_spend_path
        )
        print(f"Exported household spend to {household_spend_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
