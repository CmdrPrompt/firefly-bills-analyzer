"""UC4 write layer: create bills in Firefly III for approved recurring patterns
(FR-05a-d duplicate handling, FR-06 amount margin, FR-07b dry-run, FR-09 logging).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from firefly_python_api import BillPayload, FireflyClient, FireflyConnectionError

from firefly_bills_analyzer.analyzer import RecurringPattern
from firefly_bills_analyzer.config import Config

logger = logging.getLogger(__name__)

_REPEAT_FREQ_MAP: dict[str, str] = {
    "monthly": "monthly",
    "quarterly": "quarterly",
    "half-yearly": "half-year",
    "yearly": "yearly",
}

_NAME_UNIQUENESS_STATUS = 422


@dataclass(frozen=True)
class BillOutcome:
    """Result of attempting to create a bill for one recurring pattern (UC4)."""

    name: str
    status: str
    """One of ``"created"``, ``"exists"``, ``"exists-diff"``, ``"skipped"``, ``"error"``."""
    message: str


def _amount_range(mean: float, margin: float) -> tuple[str, str]:
    """Compute the ``±margin`` amount range around ``mean``, rounded to 2 decimals (FR-06)."""
    amount_min = round(mean * (1 - margin), 2)
    amount_max = round(mean * (1 + margin), 2)
    return f"{amount_min:.2f}", f"{amount_max:.2f}"


def _find_duplicate(
    candidate_name: str, existing_bills: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return the first existing bill whose trimmed name matches ``candidate_name`` (FR-05a)."""
    trimmed = candidate_name.strip()
    for bill in existing_bills:
        if bill["attributes"]["name"].strip() == trimmed:
            return bill
    return None


def _duplicate_outcome(
    name: str, amount_min: str, amount_max: str, repeat_freq: str, existing: dict[str, Any]
) -> BillOutcome:
    attrs = existing["attributes"]
    diffs: list[str] = []
    if attrs["amount_min"] != amount_min:
        diffs.append(f"amount_min: candidate={amount_min} existing={attrs['amount_min']}")
    if attrs["amount_max"] != amount_max:
        diffs.append(f"amount_max: candidate={amount_max} existing={attrs['amount_max']}")
    if attrs["repeat_freq"] != repeat_freq:
        diffs.append(f"repeat_freq: candidate={repeat_freq} existing={attrs['repeat_freq']}")

    if not diffs:
        return BillOutcome(name=name, status="exists", message="already exists")
    return BillOutcome(name=name, status="exists-diff", message="; ".join(diffs))


def create_bills(
    patterns: list[RecurringPattern],
    client: FireflyClient,
    config: Config,
    dry_run: bool,
    *,
    force: bool = False,
) -> list[BillOutcome]:
    """Create a Firefly III bill for each approved ``pattern`` (UC4).

    Duplicate detection follows FR-05a-d: an existing bill is a duplicate when
    its name equals the candidate's, compared case-sensitively after trimming.
    A duplicate with identical amount range and ``repeat_freq`` reports
    ``"exists"`` (FR-05b); any difference reports ``"exists-diff"`` with the
    differing values (FR-05c). No local duplicate, but the POST is rejected by
    Firefly III with a 422 name-uniqueness error, also reports ``"exists"``
    (FR-05d). In dry-run mode every outcome is ``"skipped"`` and no POST is
    made (FR-07b). ``irregular`` patterns are skipped unless ``force=True``.
    """
    existing_bills = client.get_bills()
    outcomes: list[BillOutcome] = []

    for pattern in patterns:
        name = pattern.destination_name
        repeat_freq = _REPEAT_FREQ_MAP.get(pattern.frequency, pattern.frequency)
        amount_min, amount_max = _amount_range(pattern.amount_mean, config.amount_margin)

        if pattern.frequency == "irregular" and not force:
            outcomes.append(
                BillOutcome(name=name, status="skipped", message="irregular frequency, not created")
            )
            continue

        duplicate = _find_duplicate(name, existing_bills)
        if duplicate is not None:
            outcome = _duplicate_outcome(name, amount_min, amount_max, repeat_freq, duplicate)
            outcomes.append(outcome)
            continue

        if pattern.frequency == "irregular":
            outcomes.append(
                BillOutcome(
                    name=name,
                    status="error",
                    message="irregular frequency has no valid repeat_freq mapping",
                )
            )
            continue

        if dry_run:
            outcomes.append(BillOutcome(name=name, status="skipped", message="dry-run"))
            continue

        payload = BillPayload(
            name=name,
            amount_min=amount_min,
            amount_max=amount_max,
            date=date.today().isoformat(),
            repeat_freq=repeat_freq,
            active=True,
        )
        logger.debug("POST bill %r: %r", name, payload)
        try:
            client.create_bill(payload)
        except FireflyConnectionError as exc:
            if exc.status_code == _NAME_UNIQUENESS_STATUS:
                outcomes.append(BillOutcome(name=name, status="exists", message="already exists"))
            else:
                outcomes.append(BillOutcome(name=name, status="error", message=str(exc)))
            continue
        logger.debug("Created bill %r", name)
        outcomes.append(BillOutcome(name=name, status="created", message="created"))

    return outcomes
