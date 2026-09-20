from firefly_bills_analyzer.__main__ import build_arg_parser


def test_defaults() -> None:
    args = build_arg_parser().parse_args([])
    assert args.dry_run is False
    assert args.auto_approve is False
    assert args.clear_cache is False


def test_dry_run_flag() -> None:
    args = build_arg_parser().parse_args(["--dry-run"])
    assert args.dry_run is True


def test_auto_approve_flag() -> None:
    args = build_arg_parser().parse_args(["--auto-approve"])
    assert args.auto_approve is True


def test_clear_cache_flag() -> None:
    args = build_arg_parser().parse_args(["--clear-cache"])
    assert args.clear_cache is True


def test_help_documents_key_environment_variables() -> None:
    help_text = build_arg_parser().format_help()
    for var in (
        "FIREFLY_URL",
        "FIREFLY_TOKEN",
        "DRY_RUN",
        "EXPORT_FORMAT",
        "HIGH_CONFIDENCE_THRESHOLD",
        "INCLUDE_CATEGORIES",
        "EXCLUDE_CATEGORIES",
        "UNCATEGORIZED_BEHAVIOR",
    ):
        assert var in help_text


def test_help_documents_comma_separated_export_format_syntax() -> None:
    """FR-29: --help documents EXPORT_FORMAT as accepting a comma-separated
    list too (TASK-037)."""
    help_text = build_arg_parser().format_help()
    assert "csv" in help_text
    assert "json" in help_text
    assert "none" in help_text
    assert "csv,json" in help_text
