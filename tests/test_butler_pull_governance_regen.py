"""Regression tests for TASK-048 / TASK-051 / REQUIREMENTS_BUTLER_PULL.md.

End-to-end tests exercising the real `butler-pull` Makefile target against
real git repositories: a fixture "upstream" butler source repo (a copy of
this repo's own Makefile, templates/, claude-agents/, and claude-skills/,
the same content `git subtree add --prefix=.butler` vendors into a consumer
project) and a "consumer" repo that has already adopted it and trimmed once,
as a real project would after following the README's adoption steps.

Both scenarios add a brand-new file rather than modifying a previously
trimmed one: modifying a file that was already deleted by a prior
`butler-trim` produces a modify/delete `git subtree pull` conflict, which is
an orthogonal, pre-existing subtree limitation (tracked separately, see
TASK-039) and not what TASK-048 is about.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
TEMPLATES = REPO_ROOT / "templates"
CLAUDE_AGENTS = REPO_ROOT / "claude-agents"
CLAUDE_SKILLS = REPO_ROOT / "claude-skills"


def _run(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env or os.environ.copy()
    )
    assert result.returncode == 0, (
        f"{cmd} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    _git(["init", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)


def _build_upstream(path: Path) -> None:
    """A fixture butler source repo: this repo's real Makefile, templates/,
    claude-agents/, and claude-skills/."""
    _init_repo(path)
    shutil.copy(MAKEFILE, path / "Makefile")
    shutil.copytree(TEMPLATES, path / "templates")
    shutil.copytree(CLAUDE_AGENTS, path / "claude-agents")
    shutil.copytree(CLAUDE_SKILLS, path / "claude-skills")
    _git(["add", "-A"], cwd=path)
    _git(["commit", "-m", "initial butler"], cwd=path)


def _adopt_and_trim(consumer: Path, upstream: Path) -> None:
    """Mirror the README's adoption steps: subtree add, trim, commit.

    The consumer gets its own root Makefile that `include`s the vendored
    `.butler/Makefile`, exactly as a real adopting project does, so that
    `$(MAKE)` recursion inside `butler-pull` resolves correctly.
    """
    _init_repo(consumer)
    (consumer / "README.md").write_text("# consumer\n")
    (consumer / "Makefile").write_text("include .butler/Makefile\n")
    _git(["add", "-A"], cwd=consumer)
    _git(["commit", "-m", "initial consumer"], cwd=consumer)
    _git(
        ["subtree", "add", "--prefix=.butler", str(upstream), "main", "--squash"],
        cwd=consumer,
    )
    _run(["make", "butler-trim"], cwd=consumer, env={**os.environ, "BUTLER_REMOTE": str(upstream)})
    _git(["add", "-A"], cwd=consumer)
    _git(["commit", "-m", "trim after adopt"], cwd=consumer)


def _pull(consumer: Path, upstream: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        ["make", "butler-pull"], cwd=consumer, env={**os.environ, "BUTLER_REMOTE": str(upstream)}
    )


class TestButlerPullSkipsTrimWhenTemplatesChanged:
    """Scenario: an upstream pull that touched .butler/templates/ or
    .butler/claude-agents/ must not be trimmed away before the consumer has
    had a chance to regenerate governance files against it."""

    def test_new_agent_survives_the_pull_and_regen_picks_it_up(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_and_trim(consumer, upstream)

        new_agent = upstream / "claude-agents" / "new-example.agent.md"
        new_agent.write_text("# New Example Agent\n\nAdded by the TASK-048 test.\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-example agent"], cwd=upstream)

        result = _pull(consumer, upstream)

        pulled_agent = consumer / ".butler" / "claude-agents" / "new-example.agent.md"
        assert pulled_agent.exists(), (
            "butler-pull must not delete .butler/claude-agents/ when it changed upstream, "
            "before the consumer has regenerated governance files"
        )
        assert "generate-governance-files FORCE=1" in result.stdout
        assert "changed" in result.stdout.lower()

        # Regeneration is possible: the new content is there to copy in, using the
        # same step `generate-governance-files` performs for .claude/agents/. (We
        # don't invoke the full `generate-governance-files` target here: earlier,
        # unrelated `butler-trim` runs in this fixture already deleted templates
        # that this particular pull didn't touch, e.g. CLAUDE.md.tmpl -- restoring
        # *every* previously-trimmed file on every pull is a separate, deeper
        # subtree-merge limitation tracked under TASK-039, not what TASK-048 fixes.)
        (consumer / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        shutil.copy(pulled_agent, consumer / ".claude" / "agents" / "new-example.agent.md")
        assert (consumer / ".claude" / "agents" / "new-example.agent.md").read_text() == (
            pulled_agent.read_text()
        )

        _run(
            ["make", "butler-trim"],
            cwd=consumer,
            env={**os.environ, "BUTLER_REMOTE": str(upstream)},
        )
        assert not (consumer / ".butler" / "templates").exists(), (
            "a manually-run butler-trim after the regen must still trim as before"
        )


class TestButlerPullSkipsTrimWhenSkillsChanged:
    """Scenario: TASK-051 — an upstream pull that touched
    .butler/claude-skills/ must not be trimmed away before the consumer has
    had a chance to regenerate governance files against it."""

    def test_new_skill_survives_the_pull(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_and_trim(consumer, upstream)

        new_skill_dir = upstream / "claude-skills" / "new-example"
        new_skill_dir.mkdir()
        (new_skill_dir / "SKILL.md").write_text(
            "---\nname: new-example\ndescription: Added by the TASK-051 test.\n---\n"
        )
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-example skill"], cwd=upstream)

        result = _pull(consumer, upstream)

        pulled_skill = consumer / ".butler" / "claude-skills" / "new-example" / "SKILL.md"
        assert pulled_skill.exists(), (
            "butler-pull must not delete .butler/claude-skills/ when it changed upstream, "
            "before the consumer has regenerated governance files"
        )
        assert "generate-governance-files FORCE=1" in result.stdout
        assert "claude-skills" in result.stdout
        assert "changed" in result.stdout.lower()

        # Regeneration is possible: the new content is there to copy in, using the
        # same step `generate-governance-files` performs for .claude/skills/. (We
        # don't invoke the full `generate-governance-files` target here: earlier,
        # unrelated `butler-trim` runs in this fixture already deleted templates
        # that this particular pull didn't touch, e.g. CLAUDE.md.tmpl -- restoring
        # *every* previously-trimmed file on every pull is a separate, deeper
        # subtree-merge limitation tracked under TASK-039, not what TASK-051 fixes.
        # See TestGenerateGovernanceFilesCopiesSkills for a real invocation of the
        # copy step.)
        (consumer / ".claude" / "skills" / "new-example").mkdir(parents=True, exist_ok=True)
        shutil.copy(pulled_skill, consumer / ".claude" / "skills" / "new-example" / "SKILL.md")
        assert (consumer / ".claude" / "skills" / "new-example" / "SKILL.md").read_text() == (
            pulled_skill.read_text()
        )

        _run(
            ["make", "butler-trim"],
            cwd=consumer,
            env={**os.environ, "BUTLER_REMOTE": str(upstream)},
        )
        assert not (consumer / ".butler" / "claude-skills").exists(), (
            "a manually-run butler-trim after the regen must still trim as before"
        )


class TestGenerateGovernanceFilesCopiesSkills:
    """Scenario: TASK-051 — `generate-governance-files` must copy every
    `.butler/claude-skills/*/SKILL.md` into `.claude/skills/<name>/SKILL.md`,
    mirroring the existing `claude-agents/` -> `.claude/agents/` copy."""

    def test_skill_files_are_copied_to_claude_skills(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)

        _init_repo(consumer)
        (consumer / "README.md").write_text("# consumer\n")
        (consumer / "Makefile").write_text("include .butler/Makefile\n")
        _git(["add", "-A"], cwd=consumer)
        _git(["commit", "-m", "initial consumer"], cwd=consumer)
        _git(
            ["subtree", "add", "--prefix=.butler", str(upstream), "main", "--squash"],
            cwd=consumer,
        )

        _run(
            ["make", "generate-governance-files", "FORCE=1"],
            cwd=consumer,
            env={**os.environ, "BUTLER_REMOTE": str(upstream)},
        )

        source_skills = sorted((upstream / "claude-skills").iterdir())
        assert source_skills, "fixture upstream must ship at least one claude-skills/<name>/"
        for skill_dir in source_skills:
            copied = consumer / ".claude" / "skills" / skill_dir.name / "SKILL.md"
            assert copied.exists(), (
                f"generate-governance-files must copy claude-skills/{skill_dir.name}/SKILL.md "
                "into .claude/skills/"
            )
            assert copied.read_text() == (skill_dir / "SKILL.md").read_text()


class TestButlerPullTrimsAutomaticallyWhenTemplatesUnchanged:
    """Scenario: a pull that did not touch .butler/templates/,
    .butler/claude-agents/, or .butler/claude-skills/ behaves exactly as it
    did before TASK-048 — fetch and trim in one step, no pause."""

    def test_trim_runs_automatically_and_no_warning_is_printed(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_and_trim(consumer, upstream)

        makefile = upstream / "Makefile"
        makefile.write_text(makefile.read_text() + "\n# unrelated comment\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "update Makefile comment"], cwd=upstream)

        result = _pull(consumer, upstream)

        assert not (consumer / ".butler" / "templates").exists(), (
            "butler-pull must still auto-trim when templates/claude-agents/claude-skills "
            "did not change"
        )
        assert not (consumer / ".butler" / "claude-agents").exists()
        assert not (consumer / ".butler" / "claude-skills").exists()
        assert "generate-governance-files FORCE=1" not in result.stdout
        assert (consumer / ".butler-version").exists()


class TestButlerPullDoesNotTrimOnFailedPull:
    """Scenario: `git subtree pull` itself fails (e.g. a merge conflict from
    modifying a file `butler-trim` already deleted locally -- a separate,
    pre-existing subtree limitation, not what TASK-048 fixes). `butler-pull`
    must not run `butler-trim` on top of an unresolved, failed merge."""

    def test_trim_is_skipped_and_pull_reports_failure(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_and_trim(consumer, upstream)

        agent_tmpl = upstream / "claude-agents" / "workflow-guardian.agent.md"
        agent_tmpl.write_text(agent_tmpl.read_text() + "\nmodified upstream\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "modify an already-trimmed file"], cwd=upstream)

        version_before = (consumer / ".butler-version").read_text()

        result = subprocess.run(
            ["make", "butler-pull"],
            cwd=consumer,
            capture_output=True,
            text=True,
            env={**os.environ, "BUTLER_REMOTE": str(upstream)},
        )

        assert result.returncode != 0, "a failed subtree pull must fail the butler-pull target"
        assert (consumer / ".butler-version").read_text() == version_before, (
            "butler-trim must not re-run (and re-record the version) after a failed pull"
        )
