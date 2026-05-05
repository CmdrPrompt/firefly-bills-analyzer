import firefly_bills_analyzer


def test_package_importable() -> None:
    assert firefly_bills_analyzer is not None


def test_version_is_non_empty_string() -> None:
    assert isinstance(firefly_bills_analyzer.__version__, str)
    assert firefly_bills_analyzer.__version__ != ""
