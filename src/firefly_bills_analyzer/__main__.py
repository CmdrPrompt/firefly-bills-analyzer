"""Entry point: python -m firefly_bills_analyzer."""

from __future__ import annotations

import argparse
import sys


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="firefly-bills-analyzer",
        description=(
            "Analyze Firefly III transaction history to identify recurring payments "
            "and create bills automatically."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be created without writing to Firefly III.",
    )
    p.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Automatically approve all entries above the confidence threshold.",
    )
    p.add_argument(
        "--clear-cache",
        action="store_true",
        default=False,
        help="Clear all cached data on startup before running.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    print("firefly-bills-analyzer — not yet implemented.")
    if args.dry_run:
        print("Dry-run mode: no changes will be written.")
    if args.auto_approve:
        print("Auto-approve mode: high-confidence entries approved automatically.")
    if args.clear_cache:
        print("Cache cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
