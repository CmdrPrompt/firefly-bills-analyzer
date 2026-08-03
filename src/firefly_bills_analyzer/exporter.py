"""UC5 export layer: write analysis results to CSV or JSON (FR-08)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.household_spend import (
    HouseholdSpendRecord,
    HouseholdSpendResult,
    OneOffPurchase,
)
from firefly_bills_analyzer.income import IncomeAccountIssue, IncomeSource

_FIELDNAMES = [f.name for f in fields(RecurringPattern)]

_INCOME_SOURCE_FIELDNAMES = [f.name for f in fields(IncomeSource)]
_INCOME_FIELDNAMES = [*_INCOME_SOURCE_FIELDNAMES, "status"]

# FR-51b: `HouseholdSpendRecord` fields, renamed for export; `monthly_totals`
# is internal (not exported per FR-51b's field list) and any field not
# listed here passes through under its own name, so a new dataclass field
# flows through without an exporter change (FR-51b/AC-11).
_HOUSEHOLD_SPEND_RECORD_RENAME = {
    "source_account": "source_account_name",
    "category": "category_name",
    "month_count": "complete_months",
    "median": "median_monthly",
    "mean": "mean_monthly",
    "minimum": "min_monthly",
    "maximum": "max_monthly",
}
_HOUSEHOLD_SPEND_RECORD_EXCLUDE = frozenset({"monthly_totals"})

# FR-51c: `OneOffPurchase` fields, renamed for export.
_ONE_OFF_PURCHASE_RENAME = {
    "payee": "destination_name",
    "category": "category_name",
    "source_account": "source_account_name",
}


def _renamed_fieldnames(
    cls: type, rename: dict[str, str], exclude: frozenset[str] = frozenset()
) -> list[str]:
    return [rename.get(f.name, f.name) for f in fields(cls) if f.name not in exclude]


_HOUSEHOLD_SPEND_RECORD_FIELDNAMES = _renamed_fieldnames(
    HouseholdSpendRecord, _HOUSEHOLD_SPEND_RECORD_RENAME, _HOUSEHOLD_SPEND_RECORD_EXCLUDE
)
_ONE_OFF_PURCHASE_FIELDNAMES = _renamed_fieldnames(OneOffPurchase, _ONE_OFF_PURCHASE_RENAME)

_HOUSEHOLD_SPEND_EXPORT_FIELDNAMES: list[str] = ["record_type"]
for _name in (
    *_HOUSEHOLD_SPEND_RECORD_FIELDNAMES,
    *_ONE_OFF_PURCHASE_FIELDNAMES,
    "include_tag_count",
    "exclude_tag_count",
):
    if _name not in _HOUSEHOLD_SPEND_EXPORT_FIELDNAMES:
        _HOUSEHOLD_SPEND_EXPORT_FIELDNAMES.append(_name)


def export(patterns: list[RecurringPattern], fmt: str, path: str | Path) -> None:
    """Write ``patterns`` to ``path`` in ``fmt`` (``"csv"``, ``"json"``, or ``"none"``).

    ``fmt="none"`` is a no-op: nothing is written and ``path`` need not exist
    afterwards.
    """
    if fmt == "none":
        return
    if fmt == "csv":
        _export_csv(patterns, Path(path))
    elif fmt == "json":
        _export_json(patterns, Path(path))
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}")


def _export_csv(patterns: list[RecurringPattern], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for pattern in patterns:
            writer.writerow(asdict(pattern))


def _export_json(patterns: list[RecurringPattern], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in patterns], f, indent=2)


def _income_source_row(source: IncomeSource) -> dict[str, Any]:
    """A qualifying income source's row, carrying `status` `ok` (FR-45c)."""
    row = asdict(source)
    row["status"] = "ok"
    return row


def _income_issue_row(issue: IncomeAccountIssue) -> dict[str, Any]:
    """A no-qualifying-candidate/ambiguous account's row (FR-45c).

    `payer` and `observed_net_income` are left empty: no single candidate
    was resolved, so nothing can be reported for either field. `status`
    carries the reason plus the candidate payers that were considered.
    """
    row: dict[str, Any] = dict.fromkeys(_INCOME_SOURCE_FIELDNAMES, "")
    row["income_account"] = issue.income_account
    candidates = ", ".join(candidate.payer for candidate in issue.candidates)
    row["status"] = f"{issue.reason} (candidates: {candidates})"
    return row


def export_income(
    sources: list[IncomeSource],
    issues: list[IncomeAccountIssue],
    fmt: str,
    path: str | Path,
) -> None:
    """Write income sources and reported-issue accounts to `path` (FR-45a).

    ``fmt="none"`` is a no-op: nothing is written and ``path`` need not exist
    afterwards. The field list is derived from `IncomeSource`'s own fields
    (`_INCOME_FIELDNAMES`) plus `status`, matching how `_FIELDNAMES` is
    derived for the pattern export, so a later field addition to
    `IncomeSource` flows through without an exporter change (FR-45b).
    """
    if fmt == "none":
        return
    rows = [_income_source_row(source) for source in sources] + [
        _income_issue_row(issue) for issue in issues
    ]
    if fmt == "csv":
        _export_income_csv(rows, Path(path))
    elif fmt == "json":
        _export_income_json(rows, Path(path))
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}")


def _export_income_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_INCOME_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _export_income_json(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def _household_spend_record_row(record: HouseholdSpendRecord) -> dict[str, Any]:
    """A household spend record's row (FR-51b), tagged `record_type` `household-spend`.

    A record produced under FR-49e (fewer than the configured minimum months)
    carries `median_monthly` as `None`, which serializes as an empty CSV cell
    or JSON `null` (AC-6).
    """
    row = {
        _HOUSEHOLD_SPEND_RECORD_RENAME.get(f.name, f.name): getattr(record, f.name)
        for f in fields(record)
        if f.name not in _HOUSEHOLD_SPEND_RECORD_EXCLUDE
    }
    row["record_type"] = "household-spend"
    return row


def _one_off_purchase_row(purchase: OneOffPurchase) -> dict[str, Any]:
    """A one-off purchase's row (FR-51c), tagged `record_type` `one-off`."""
    row = {
        _ONE_OFF_PURCHASE_RENAME.get(f.name, f.name): getattr(purchase, f.name)
        for f in fields(purchase)
    }
    row["record_type"] = "one-off"
    return row


def _unmatched_category_row(category: str) -> dict[str, Any]:
    """A configured category matching no transaction (FR-50)."""
    return {"record_type": "unmatched-category", "category_name": category}


def _tag_counts_row(include_tag_count: int, exclude_tag_count: int) -> dict[str, Any]:
    """The include/exclude tag correction counts (FR-48f)."""
    return {
        "record_type": "tag-counts",
        "include_tag_count": include_tag_count,
        "exclude_tag_count": exclude_tag_count,
    }


def export_household_spend(result: HouseholdSpendResult, fmt: str, path: str | Path) -> None:
    """Write household spend records and one-off purchases to `path` (FR-51a).

    ``fmt="none"`` is a no-op: nothing is written and ``path`` need not exist
    afterwards. Household spend rows, one-off purchase rows, unmatched
    categories (FR-50), and the include/exclude tag counts (FR-48f) share one
    file, distinguished by a `record_type` column rather than which fields are
    empty (FR-51c). The field list is derived from `HouseholdSpendRecord` and
    `OneOffPurchase`'s own fields, so a later field addition to either
    dataclass flows through without an exporter change (AC-11).
    """
    if fmt == "none":
        return
    rows: list[dict[str, Any]] = [_household_spend_record_row(r) for r in result.records]
    rows += [_one_off_purchase_row(p) for p in result.one_off_purchases]
    rows += [_unmatched_category_row(c) for c in result.unmatched_categories]
    rows.append(_tag_counts_row(result.include_tag_count, result.exclude_tag_count))
    if fmt == "csv":
        _export_household_spend_csv(rows, Path(path))
    elif fmt == "json":
        _export_household_spend_json(rows, Path(path))
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}")


def _export_household_spend_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HOUSEHOLD_SPEND_EXPORT_FIELDNAMES, restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _export_household_spend_json(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
