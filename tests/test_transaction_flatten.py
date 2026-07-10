"""Hypothesis-driven tests for the withdrawal-split-to-TransactionRead transform."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from firefly_python_api._client import _split_to_transaction_read

# Firefly III datetimes are full ISO-8601, e.g. "2024-03-15T14:32:07+00:00".
_iso_datetime = st.builds(
    lambda dt, offset_minutes: (dt + timedelta(minutes=offset_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    ),
    st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 1, 1)),
    st.integers(min_value=0, max_value=0),
)

_amount = st.decimals(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False).map(
    lambda d: str(d)
)

_optional_name = st.one_of(st.none(), st.text(min_size=1, max_size=50))


@st.composite
def _split_dict(draw: st.DrawFn) -> dict[str, object]:
    split: dict[str, object] = {
        "date": draw(_iso_datetime),
        "amount": draw(_amount),
    }
    destination_name = draw(_optional_name)
    if destination_name is not None or draw(st.booleans()):
        split["destination_name"] = destination_name
    category_name = draw(_optional_name)
    if category_name is not None or draw(st.booleans()):
        split["category_name"] = category_name
    return split


class TestSplitToTransactionRead:
    @given(_split_dict())
    def test_date_is_always_truncated_to_ten_chars(self, split: dict[str, object]) -> None:
        result = _split_to_transaction_read(split)
        assert len(result["date"]) == 10
        assert result["date"] == split["date"][:10]  # type: ignore[index]

    @given(_split_dict())
    def test_amount_is_preserved(self, split: dict[str, object]) -> None:
        result = _split_to_transaction_read(split)
        assert result["amount"] == split["amount"]

    @given(_split_dict())
    def test_missing_destination_name_defaults_to_none(self, split: dict[str, object]) -> None:
        split.pop("destination_name", None)
        result = _split_to_transaction_read(split)
        assert result["destination_name"] is None

    @given(_split_dict())
    def test_missing_category_name_defaults_to_none(self, split: dict[str, object]) -> None:
        split.pop("category_name", None)
        result = _split_to_transaction_read(split)
        assert result["category_name"] is None

    @given(_split_dict())
    def test_present_optional_fields_are_preserved(self, split: dict[str, object]) -> None:
        split["destination_name"] = "Some Shop"
        split["category_name"] = "Some Category"
        result = _split_to_transaction_read(split)
        assert result["destination_name"] == "Some Shop"
        assert result["category_name"] == "Some Category"
