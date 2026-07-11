"""UC5 export layer: write analysis results to CSV or JSON (FR-08)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, fields
from pathlib import Path

from firefly_bills_analyzer.analyzer import RecurringPattern

_FIELDNAMES = [f.name for f in fields(RecurringPattern)]


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
