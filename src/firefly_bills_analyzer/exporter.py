"""UC5 export layer: write analysis results to CSV or JSON (FR-08)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.income import IncomeAccountIssue, IncomeSource

_FIELDNAMES = [f.name for f in fields(RecurringPattern)]

_INCOME_SOURCE_FIELDNAMES = [f.name for f in fields(IncomeSource)]
_INCOME_FIELDNAMES = [*_INCOME_SOURCE_FIELDNAMES, "status"]


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
