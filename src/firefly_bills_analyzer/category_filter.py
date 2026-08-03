"""UC6 category filtering: include/exclude lists and uncategorized handling."""

from __future__ import annotations

from collections import Counter

from firefly_python_api import TransactionRead

from firefly_bills_analyzer.config import Config


def filter_transactions(
    transactions: list[TransactionRead], config: Config
) -> list[TransactionRead]:
    """Filter transactions by category include/exclude lists (FR-11a, FR-11b)
    and the configured uncategorized-transaction behavior (FR-14).

    Uncategorized transactions bypass the include/exclude lists entirely:
    they are kept when ``config.uncategorized_behavior`` is ``"include"`` or
    ``"neutral"``, and dropped when it is ``"exclude"``. Exclude is applied
    after include for categorized transactions.
    """
    include = set(config.include_categories)
    exclude = set(config.exclude_categories)

    result = []
    for transaction in transactions:
        category = transaction["category_name"]
        if category is None:
            if config.uncategorized_behavior != "exclude":
                result.append(transaction)
            continue
        if include and category not in include:
            continue
        if category in exclude:
            continue
        result.append(transaction)
    return result


def resolve_category_name(
    transactions_for_cluster: list[TransactionRead], config: Config
) -> str | None:
    """Return the category name accounting for at least
    ``config.category_majority_threshold`` of an amount cluster's
    transactions (FR-13b).

    The share is computed over the cluster passed in, not over all of a
    payee's transactions, so that a payee bundling several distinct
    recurring charges under one name resolves a category name per cluster
    rather than one name for all of them. Uncategorized transactions count
    as their own non-matching bucket, so a majority of uncategorized
    transactions also resolves to ``None``. When two or more categories are
    tied for most frequent, no category name is resolved, regardless of
    ``config.category_majority_threshold``.
    """
    if not transactions_for_cluster:
        return None

    counts = Counter[str | None](t["category_name"] for t in transactions_for_cluster)
    ranked = counts.most_common()
    category, count = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == count:
        return None
    if category is None:
        return None
    if count / len(transactions_for_cluster) >= config.category_majority_threshold:
        return str(category)
    return None
