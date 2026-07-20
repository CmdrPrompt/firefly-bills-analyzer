"""Tests for TASK-027: packaging and optionality (Requirement 9).

Covers CLI entry-point declaration, the MCP server's independent, dev-dependency-free
packaging, the PyPI-name collision guard against the `mcp` SDK package, and the README
documenting CLI/MCP installation as optional additions.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


class TestRootEntryPoint:
    def test_butler_script_points_at_cli_main(self) -> None:
        data = _load_toml(REPO_ROOT / "pyproject.toml")

        scripts = data["project"]["scripts"]
        assert scripts.get("butler") == "butler_cli.__main__:main", (
            f"expected 'butler' entry point to target butler_cli.__main__:main, got {scripts!r}"
        )


class TestMcpPackagingIsolation:
    def test_distribution_name_is_not_mcp(self) -> None:
        """Guards against a namespace collision with the official `mcp` SDK on PyPI,
        which the server depends on (see REQUIREMENTS_MCP.md Requirement 9,
        namespace collision constraint)."""
        data = _load_toml(REPO_ROOT / "mcp" / "pyproject.toml")

        name = data["project"]["name"]
        assert name != "mcp", (
            f"MCP server distribution name must not be 'mcp' — that name belongs to "
            f"the official MCP SDK it depends on, got {name!r}"
        )

    def test_depends_on_butler_core_and_mcp_sdk(self) -> None:
        data = _load_toml(REPO_ROOT / "mcp" / "pyproject.toml")

        deps = data["project"]["dependencies"]
        assert any(d.startswith("butler-core") for d in deps), (
            f"expected mcp/pyproject.toml to depend on butler-core, got {deps!r}"
        )
        assert any(d.startswith("mcp") for d in deps), (
            f"expected mcp/pyproject.toml to depend on the mcp SDK, got {deps!r}"
        )

    def test_runtime_dependencies_exclude_butler_core_dev_extras(self) -> None:
        """`butler_core`'s dev dependencies (ruff, mypy, pytest, hypothesis, ...) must
        not leak into the MCP server's install when a consumer runs `pip install
        ./mcp` — only butler-core's runtime deps and the MCP SDK should be pulled
        in."""
        core_data = _load_toml(REPO_ROOT / "pyproject.toml")
        dev_deps = set(core_data["project"]["optional-dependencies"]["dev"])

        mcp_data = _load_toml(REPO_ROOT / "mcp" / "pyproject.toml")
        runtime_deps = set(mcp_data["project"]["dependencies"])

        leaked = {dep for dep in runtime_deps if dep.split(">=")[0].split("==")[0] in dev_deps}
        assert not leaked, (
            f"mcp/pyproject.toml runtime dependencies must not include butler_core's "
            f"dev extras, but found {leaked!r}"
        )

    def test_no_top_level_init_in_mcp_source_directory(self) -> None:
        """The `mcp/` source directory must not gain a top-level `__init__.py`: doing
        so would make it an explicit regular package, which, combined with its name
        colliding with the `mcp` SDK's, worsens the namespace-shadowing risk if the
        repo root ever lands on sys.path (see REQUIREMENTS_MCP.md Requirement 9,
        namespace collision constraint)."""
        assert not (REPO_ROOT / "mcp" / "__init__.py").exists(), (
            "mcp/__init__.py must not exist — it would make the local mcp/ directory "
            "an explicit package shadowing the mcp SDK dependency"
        )


class TestMakefileOnlyFallback:
    def test_check_butler_target_fails_with_clear_message_when_cli_missing(
        self, tmp_path: Path
    ) -> None:
        """A project that only adopted `.butler/Makefile` (no butler_cli installed)
        must see a clear, actionable error — not a cryptic Python traceback — from
        any task target (Requirement 8's constraint, re-verified here as part of
        TASK-027's Makefile-only adoption acceptance criterion)."""
        empty_bin = tmp_path / "empty-bin"
        empty_bin.mkdir()
        stripped_path = f"{empty_bin}:/usr/bin:/bin"

        result = subprocess.run(
            ["make", "check-butler"],
            cwd=REPO_ROOT,
            env={"PATH": stripped_path},
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "check-butler should fail when butler is not on PATH"
        assert "Traceback" not in result.stdout + result.stderr, (
            f"expected a clean error, not a Python traceback, "
            f"got stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "butler-cli is not installed" in result.stdout, (
            f"expected a message pointing at how to install butler-cli, "
            f"got stdout={result.stdout!r}"
        )


class TestReadmeDocumentsOptionalInstalls:
    def test_documents_cli_installation_as_optional(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text()

        assert "uv tool install" in readme, (
            "expected README to document `uv tool install` for the CLI"
        )
        cli_section_present = "## CLI" in readme or "## Installing the CLI" in readme
        assert cli_section_present, "expected a README section documenting CLI installation"

    def test_cli_section_is_marked_optional(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text()

        idx = readme.find("uv tool install")
        assert idx != -1, "expected README to mention `uv tool install`"
        surrounding = readme[max(0, idx - 500) : idx + 500]
        assert "optional" in surrounding.lower(), (
            "expected the CLI installation section to be clearly marked as optional"
        )

    def test_documents_mcp_server_setup_as_optional(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text()

        mcp_section_present = "## MCP" in readme or "MCP server" in readme
        assert mcp_section_present, "expected a README section documenting MCP server setup"

        idx = readme.lower().find("mcp server")
        assert idx != -1, "expected README to mention the MCP server"
        surrounding = readme[max(0, idx - 500) : idx + 500]
        assert "optional" in surrounding.lower(), (
            "expected the MCP server section to be clearly marked as optional"
        )
