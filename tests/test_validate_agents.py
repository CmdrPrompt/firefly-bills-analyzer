"""Characterization tests for scripts/validate_agents.py.

These tests document the current, verified behavior of the agent frontmatter
validator. They do not assert what the "right" behavior should be -- only
what the script actually does today.

`scripts/` is not a Python package, so the module is loaded by file path via
importlib, matching the fact that this script is invoked as a standalone CLI
(python3 scripts/validate_agents.py) rather than imported from an installed
package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_agents.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_agents", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def validate_agents() -> ModuleType:
    return _load_module()


def _write_agent(path: Path, frontmatter: str, body: str = "Body text.\n") -> Path:
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return path


class TestParseFrontmatter:
    def test_parses_scalar_and_list_values(self, validate_agents: ModuleType) -> None:
        text = (
            "---\n"
            "name: My Agent\n"
            'description: "Does things"\n'
            "tools: [Read, Write, Bash]\n"
            "---\n"
            "Body\n"
        )

        fm = validate_agents.parse_frontmatter(text)

        assert fm == {
            "name": "My Agent",
            "description": "Does things",
            "tools": ["Read", "Write", "Bash"],
        }

    def test_returns_none_when_no_frontmatter_delimiters(self, validate_agents: ModuleType) -> None:
        assert validate_agents.parse_frontmatter("just a plain markdown file\n") is None

    def test_returns_none_when_frontmatter_not_closed(self, validate_agents: ModuleType) -> None:
        text = "---\nname: Foo\ndescription: bar\n"

        assert validate_agents.parse_frontmatter(text) is None

    def test_skips_blank_lines_and_comments_in_frontmatter(
        self, validate_agents: ModuleType
    ) -> None:
        text = "---\n# a comment\n\nname: Foo\ndescription: bar\n---\nBody\n"

        fm = validate_agents.parse_frontmatter(text)

        assert fm == {"name": "Foo", "description": "bar"}

    def test_ignores_lines_without_a_colon(self, validate_agents: ModuleType) -> None:
        text = "---\nname: Foo\ndescription: bar\nnot-a-key-value-line\n---\nBody\n"

        fm = validate_agents.parse_frontmatter(text)

        assert fm == {"name": "Foo", "description": "bar"}


class TestValidateFile:
    def test_valid_definition_has_no_errors(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "good.agent.md",
            "name: Good Agent\ndescription: A good agent\ntools: [Read, Grep]",
        )

        errors = validate_agents.validate_file(path)

        assert errors == [], f"expected no errors for a valid file, got {errors!r}"

    def test_unknown_tool_name_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "bad.agent.md",
            "name: Bad Agent\ndescription: desc\ntools: [Frobnicate]",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "unknown tool 'Frobnicate'" in errors[0]

    def test_case_mismatch_tool_produces_did_you_mean_hint(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "case.agent.md",
            "name: Case Agent\ndescription: desc\ntools: [read, write]",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 2
        assert "did you mean 'Read'?" in errors[0]
        assert "did you mean 'Write'?" in errors[1]

    def test_empty_tools_list_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "empty.agent.md",
            "name: Empty Agent\ndescription: desc\ntools: []",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "'tools' is empty" in errors[0]

    def test_missing_name_key_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "no_name.agent.md",
            "description: desc\ntools: [Read]",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "missing required key 'name'" in errors[0]

    def test_missing_description_key_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "no_desc.agent.md",
            "name: Foo\ntools: [Read]",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "missing required key 'description'" in errors[0]

    def test_missing_frontmatter_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = tmp_path / "no_frontmatter.agent.md"
        path.write_text("Just a plain file with no frontmatter at all.\n", encoding="utf-8")

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "missing or malformed YAML frontmatter" in errors[0]

    def test_mcp_shaped_tool_name_is_accepted(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "mcp.agent.md",
            "name: MCP Agent\ndescription: desc\ntools: [Read, mcp__github__list_prs]",
        )

        errors = validate_agents.validate_file(path)

        assert errors == [], f"expected mcp-shaped tool name to be accepted, got {errors!r}"

    def test_missing_tools_key_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        # A missing `tools:` key leaves the agent with no tools at runtime,
        # exactly like an empty list -- so it is a required key too.
        path = _write_agent(
            tmp_path / "no_tools_key.agent.md",
            "name: Foo\ndescription: desc",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "missing required key 'tools'" in errors[0]

    def test_allow_tool_free_true_has_no_errors(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "opt_out.agent.md",
            "name: Foo\ndescription: desc\ntools: [Read]\nallow-tool-free: true",
        )

        errors = validate_agents.validate_file(path)

        assert errors == [], f"expected no errors for allow-tool-free: true, got {errors!r}"

    def test_allow_tool_free_false_has_no_errors(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "opt_out_false.agent.md",
            "name: Foo\ndescription: desc\ntools: [Read]\nallow-tool-free: false",
        )

        errors = validate_agents.validate_file(path)

        assert errors == [], f"expected no errors for allow-tool-free: false, got {errors!r}"

    def test_allow_tool_free_non_boolean_value_is_reported(
        self, tmp_path: Path, validate_agents: ModuleType
    ) -> None:
        path = _write_agent(
            tmp_path / "opt_out_bad.agent.md",
            "name: Foo\ndescription: desc\ntools: [Read]\nallow-tool-free: yes",
        )

        errors = validate_agents.validate_file(path)

        assert len(errors) == 1
        assert "'allow-tool-free' must be a boolean" in errors[0]


class TestMain:
    def test_all_valid_files_exit_zero_with_summary(
        self,
        tmp_path: Path,
        validate_agents: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _write_agent(tmp_path / "a.agent.md", "name: A\ndescription: a\ntools: [Read]")
        _write_agent(tmp_path / "b.agent.md", "name: B\ndescription: b\ntools: [Write]")
        monkeypatch.setattr(sys, "argv", ["validate_agents.py", str(tmp_path)])

        exit_code = validate_agents.main()

        out = capsys.readouterr().out
        assert exit_code == 0
        assert "validate-agents: OK" in out
        assert "2 agent definitions valid" in out

    def test_any_failure_exits_one_with_fail_summary_and_bullets(
        self,
        tmp_path: Path,
        validate_agents: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _write_agent(tmp_path / "good.agent.md", "name: A\ndescription: a\ntools: [Read]")
        _write_agent(tmp_path / "bad.agent.md", "name: B\ndescription: b\ntools: [NotAThing]")
        monkeypatch.setattr(sys, "argv", ["validate_agents.py", str(tmp_path)])

        exit_code = validate_agents.main()

        out = capsys.readouterr().out
        assert exit_code == 1
        assert "validate-agents: FAIL" in out
        assert "1 error(s)" in out
        assert "bad.agent.md: unknown tool 'NotAThing'" in out

    def test_nonexistent_directory_exits_one(
        self,
        tmp_path: Path,
        validate_agents: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        missing = tmp_path / "does_not_exist"
        monkeypatch.setattr(sys, "argv", ["validate_agents.py", str(missing)])

        exit_code = validate_agents.main()

        out = capsys.readouterr().out
        assert exit_code == 1
        assert "directory not found" in out

    def test_directory_with_no_agent_files_exits_one(
        self,
        tmp_path: Path,
        validate_agents: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / "readme.md").write_text("not an agent file\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["validate_agents.py", str(tmp_path)])

        exit_code = validate_agents.main()

        out = capsys.readouterr().out
        assert exit_code == 1
        assert "no *.agent.md files" in out

    def test_defaults_to_dot_claude_agents_when_no_arg_given(
        self,
        tmp_path: Path,
        validate_agents: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["validate_agents.py"])

        exit_code = validate_agents.main()

        out = capsys.readouterr().out
        assert exit_code == 1
        assert "directory not found: .claude/agents" in out
