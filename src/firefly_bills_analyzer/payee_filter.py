"""UC10 destination payee filtering: include/exclude lists."""

from __future__ import annotations

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.config import Config


def filter_transactions(
    transactions: list[TransactionRead], config: Config
) -> list[TransactionRead]:
    """Filter transactions by destination-payee include/exclude lists (FR-36a, FR-36b).

    Transactions with ``destination_name is None`` never match a non-empty
    include or exclude list. Exclude is applied after include when both are
    configured.
    """
    include = set(config.include_payees)
    exclude = set(config.exclude_payees)

    result = []
    for transaction in transactions:
        destination = transaction["destination_name"]
        if include and destination not in include:
            continue
        if destination in exclude:
            continue
        result.append(transaction)
    return result
