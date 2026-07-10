"""UC1 data-ingestion layer: fetch withdrawal transactions from Firefly III."""

from __future__ import annotations

import calendar
import logging
from datetime import date
from typing import cast

from firefly_python_api import FireflyClient, FireflyConnectionError, TransactionRead

from firefly_bills_analyzer.config import Config

logger = logging.getLogger(__name__)


def _today() -> date:
    return date.today()


def _subtract_months(reference: date, months: int) -> date:
    """Return ``reference`` minus ``months`` calendar months.

    Clamps the day-of-month to the target month's length (e.g. Mar 31 minus
    1 month becomes Feb 28/29) rather than overflowing into the next month.
    """
    total_months = reference.year * 12 + (reference.month - 1) - months
    year, month = divmod(total_months, 12)
    month += 1
    day = min(reference.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def fetch_transactions(config: Config) -> list[TransactionRead]:
    """Fetch all withdrawal transactions in the configured lookback window.

    Parameters
    ----------
    config:
        Runtime configuration; ``lookback_months`` sets the window start
        (today minus that many calendar months), ``firefly_url``/
        ``firefly_token`` authenticate the request.

    Returns
    -------
    list[TransactionRead]
        Flattened withdrawal transaction splits.
    """
    end = _today()
    start = _subtract_months(end, config.lookback_months)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    client = FireflyClient(config.firefly_url, config.firefly_token)

    logger.debug("Calling get_withdrawal_transactions(%s, %s)", start_str, end_str)
    try:
        transactions = client.get_withdrawal_transactions(start_str, end_str)
    except FireflyConnectionError as exc:
        logger.debug("get_withdrawal_transactions failed: %s", exc)
        raise SystemExit(f"Could not fetch transactions from Firefly III: {exc}") from exc

    logger.debug("get_withdrawal_transactions succeeded: %d transaction(s)", len(transactions))
    return cast(list[TransactionRead], transactions)
