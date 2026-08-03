"""Hypothesis-driven tests for the tags field of _split_to_transaction_read (REQ-012)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from firefly_python_api._client import _split_to_transaction_read

_base_split = {"date": "2024-03-15T14:32:07+00:00", "amount": "10.00"}

_tag_string = st.text(min_size=0, max_size=50)
_tag_list = st.lists(_tag_string, min_size=0, max_size=5)


class TestSplitToTransactionReadTags:
    def test_missing_tags_key_defaults_to_empty_list(self) -> None:
        split = dict(_base_split)
        result = _split_to_transaction_read(split)
        assert result["tags"] == []
        assert result["tags"] is not None

    def test_null_tags_defaults_to_empty_list(self) -> None:
        split = {**_base_split, "tags": None}
        result = _split_to_transaction_read(split)
        assert result["tags"] == []

    @given(_tag_list)
    def test_tags_are_preserved_in_order(self, tags: list[str]) -> None:
        split = {**_base_split, "tags": tags}
        result = _split_to_transaction_read(split)
        assert result["tags"] == tags

    @given(st.text(min_size=1, max_size=50))
    def test_tag_string_is_not_case_folded_trimmed_or_sorted(self, raw_tag: str) -> None:
        split = {**_base_split, "tags": [raw_tag]}
        result = _split_to_transaction_read(split)
        assert result["tags"][0] == raw_tag

    def test_tags_never_none_even_when_absent(self) -> None:
        split = dict(_base_split)
        result = _split_to_transaction_read(split)
        assert result["tags"] is not None
        assert isinstance(result["tags"], list)
