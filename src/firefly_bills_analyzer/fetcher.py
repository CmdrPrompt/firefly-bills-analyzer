"""UC1 data-ingestion layer: fetch withdrawal transactions from Firefly III."""

from __future__ import annotations

import calendar
import logging
from datetime import date
from pathlib import Path
from typing import cast

from firefly_python_api import FireflyClient, FireflyConnectionError, TransactionRead
from tqdm import tqdm

from firefly_bills_analyzer import cache
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

    cache_dir = Path(config.cache_dir)
    cached = cache.read("transactions", config.cache_ttl_transactions, cache_dir)
    if cached is not None and cached["start"] == start_str and cached["end"] == end_str:
        logger.debug(
            "Using cached transactions for %s..%s (%d transaction(s))",
            start_str,
            end_str,
            len(cached["transactions"]),
        )
        return cast(list[TransactionRead], cached["transactions"])

    client = FireflyClient(config.firefly_url, config.firefly_token)

    logger.debug("Calling get_withdrawal_transactions(%s, %s)", start_str, end_str)
    try:
        with tqdm(desc="Fetching transactions", unit="page") as bar:

            def on_page(page: int, total_pages: int) -> None:
                if bar.total is None:
                    bar.total = total_pages
                bar.update(1)

            transactions = client.get_withdrawal_transactions(start_str, end_str, on_page=on_page)
    except FireflyConnectionError as exc:
        logger.debug("get_withdrawal_transactions failed: %s", exc)
        raise SystemExit(f"Could not fetch transactions from Firefly III: {exc}") from exc

    logger.debug("get_withdrawal_transactions succeeded: %d transaction(s)", len(transactions))
    cache.write(
        "transactions",
        {"start": start_str, "end": end_str, "transactions": transactions},
        cache_dir,
    )
    return cast(list[TransactionRead], transactions)
