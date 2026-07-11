"""Regression tests for TASK-044 / REQUIREMENTS_TASK_WORKFLOW.md Requirement 2.

Guards against drift between the `butler ...` invocations in the root
Makefile and the flags the installed CLI's argparse definition
(`src/butler_cli/__main__.py`) actually accepts: every flag the Makefile
passes must be recognized by the CLI, or `make test` must fail.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from butler_cli.__main__ import _build_parser

_LONG_FLAG_RE = re.compile(r"--[a-zA-Z][a-zA-Z0-9-]*")

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _extract_butler_invocation_flags(makefile_text: str) -> set[str]:
    """Return every long flag (e.g. `--tasks-dir`) passed on any Makefile
    line that invokes the `butler` CLI. Lines that merely mention the word
    "butler" without invoking the binary (comments, `@echo` help text,
    target names such as `check-butler:`) are ignored."""
    flags: set[str] = set()
    for raw_line in makefile_text.splitlines():
        line = raw_line.strip().lstrip("@")
        if not line or line.startswith("#"):
            continue
        if not re.search(r"(?<![\w.-])butler(?![\w-])\s", line):
            # Only lines invoking the standalone `butler` command followed by
            # an argument count; excludes ".butler" paths (e.g. git subtree
            # commands), hyphenated target/mentions like "check-butler" or
            # "butler-check", and lines where "butler" has no invocation
            # arguments (comments, echoed help text).
            continue
        flags.update(_LONG_FLAG_RE.findall(line))
    return flags


def _collect_accepted_flags(parser: argparse.ArgumentParser) -> set[str]:
    """Recursively collect every long option string accepted anywhere in the
    parser tree: the top-level parser plus every nested subparser."""
    flags: set[str] = set()
    for action in parser._actions:  # noqa: SLF001 -- no public API for this
        flags.update(opt for opt in action.option_strings if opt.startswith("--"))
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for subparser in action.choices.values():
                flags |= _collect_accepted_flags(subparser)
    return flags


class TestExtractButlerInvocationFlags:
    """Scenario: Test parses butler invocations from root Makefile."""

    def test_extracts_tasks_dir_flag_from_simple_invocation(self) -> None:
        makefile_text = (
            "branch-task: check-butler\n\tbutler --tasks-dir $(TASKS_DIR) task branch $(f)\n"
        )
        assert _extract_butler_invocation_flags(makefile_text) == {"--tasks-dir"}

    def test_ignores_target_names_and_comments_mentioning_butler(self) -> None:
        makefile_text = (
            "# make butler-check -- Check if butler updates are available\n"
            "check-butler:\n"
            "\t@command -v butler > /dev/null 2>&1 || echo missing\n"
        )
        assert _extract_butler_invocation_flags(makefile_text) == set()

    def test_extracts_flags_from_multiple_invocation_lines(self) -> None:
        makefile_text = (
            "\tbutler --tasks-dir $(TASKS_DIR) task branch $(f)\n"
            "\tbutler --tasks-dir $(TASKS_DIR) task pr $(f)\n"
        )
        assert _extract_butler_invocation_flags(makefile_text) == {"--tasks-dir"}

    def test_parses_real_root_makefile_without_error(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        flags = _extract_butler_invocation_flags(makefile_text)
        assert flags == {"--tasks-dir"}


class TestCollectAcceptedFlags:
    """Helper sanity check: the CLI-introspection side of the comparison."""

    def test_collects_top_level_and_nested_subparser_flags(self) -> None:
        parser = _build_parser()
        flags = _collect_accepted_flags(parser)
        assert "--tasks-dir" in flags
        assert "--status" in flags
        assert "--categories" in flags


class TestMakefileFlagsAcceptedByCli:
    """Scenario: Test cross-checks Makefile flags against CLI argparse, and
    Scenario: Test passes if all Makefile flags are accepted."""

    def test_every_flag_the_makefile_passes_is_accepted_by_the_cli(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        makefile_flags = _extract_butler_invocation_flags(makefile_text)
        accepted_flags = _collect_accepted_flags(_build_parser())

        unrecognized = makefile_flags - accepted_flags
        assert unrecognized == set(), (
            f"Makefile passes flag(s) not accepted by the CLI's argparse "
            f"definition: {sorted(unrecognized)}"
        )


class TestDriftIsDetected:
    """Scenario: Test fails if a flag the Makefile passes is no longer
    accepted by CLI. Exercised here against a synthetic Makefile/parser pair
    (rather than mutating the real CLI) to prove the detection logic itself
    is sound."""

    def test_detects_a_flag_the_cli_no_longer_accepts(self) -> None:
        makefile_text = "\tbutler --tasks-dir $(TASKS_DIR) --deprecated-flag task branch $(f)\n"
        makefile_flags = _extract_butler_invocation_flags(makefile_text)
        accepted_flags = _collect_accepted_flags(_build_parser())

        unrecognized = makefile_flags - accepted_flags

        assert unrecognized == {"--deprecated-flag"}
