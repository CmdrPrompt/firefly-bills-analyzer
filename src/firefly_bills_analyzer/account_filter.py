"""UC9 source account filtering: include/exclude lists."""

from __future__ import annotations

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.config import Config


def filter_transactions(
    transactions: list[TransactionRead], config: Config
) -> list[TransactionRead]:
    """Filter transactions by source-account include/exclude lists (FR-35a, FR-35b).

    Transactions with ``source_name is None`` never match a non-empty include
    or exclude list. Exclude is applied after include when both are configured.
    """
    include = set(config.include_accounts)
    exclude = set(config.exclude_accounts)

    result = []
    for transaction in transactions:
        source = transaction["source_name"]
        if include and source not in include:
            continue
        if source in exclude:
            continue
        result.append(transaction)
    return result
