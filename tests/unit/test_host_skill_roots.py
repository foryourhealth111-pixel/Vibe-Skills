from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel import HostSkillRoot, resolve_host_skill_roots


def _write_skill_roots_config(path: Path, roots: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": roots}), encoding="utf-8")


def test_resolve_host_skill_roots_uses_project_user_then_skills_dir_order(tmp_path: Path) -> None:
    skills_dir = tmp_path / "home" / ".agents" / "skills"
    workspace_root = tmp_path / "workspace"
    _write_skill_roots_config(tmp_path / "home" / ".vibeskills" / "skill-roots.json", ["D:/user-skills"])
    _write_skill_roots_config(workspace_root / ".vibeskills" / "skill-roots.json", ["project-skills"])

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="codex",
        agent_root=skills_dir,
        workspace_root=workspace_root,
    )

    assert roots == (
        HostSkillRoot("codex", "workspace_extra", (workspace_root / "project-skills").resolve(), str((workspace_root / ".vibeskills" / "skill-roots.json").resolve())),
        HostSkillRoot("codex", "user_extra", Path("D:/user-skills").resolve(), str((tmp_path / "home" / ".vibeskills" / "skill-roots.json").resolve())),
        HostSkillRoot("codex", "skills_dir", skills_dir.resolve(), f"skills_dir:{skills_dir.resolve()}"),
    )


def test_resolve_host_skill_roots_uses_the_explicit_skills_dir_for_claude_code(tmp_path: Path) -> None:
    skills_dir = tmp_path / "common-skills"

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="claude-code",
        agent_root=skills_dir,
        workspace_root=None,
    )

    assert roots == (
        HostSkillRoot("claude-code", "skills_dir", skills_dir.resolve(), f"skills_dir:{skills_dir.resolve()}"),
    )


def test_resolve_host_skill_roots_includes_existing_codex_plugin_cache(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    plugin_cache = tmp_path / "home" / ".codex" / "plugins" / "cache"
    plugin_cache.mkdir(parents=True)

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="codex",
        agent_root=agent_root,
        workspace_root=None,
    )

    assert roots == (
        HostSkillRoot(
            "codex",
            "skills_dir",
            (agent_root / "skills").resolve(),
            f"skills_dir:{(agent_root / 'skills').resolve()}",
        ),
        HostSkillRoot(
            "codex",
            "codex_plugin_cache",
            plugin_cache.resolve(),
            f"codex_plugin_cache:{plugin_cache.resolve()}",
        ),
    )


def test_resolve_host_skill_roots_accepts_legacy_host_root_as_skills_parent(tmp_path: Path) -> None:
    host_root = tmp_path / "home" / ".agents"

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="codex",
        agent_root=host_root,
        workspace_root=None,
    )

    skills_dir = (host_root / "skills").resolve()
    assert roots == (
        HostSkillRoot("codex", "skills_dir", skills_dir, f"skills_dir:{skills_dir}"),
    )


def test_resolve_host_skill_roots_deduplicates_roots_by_precedence(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents" / "skills"
    workspace_root = tmp_path / "workspace"
    shared_root = tmp_path / "shared-skills"
    _write_skill_roots_config(tmp_path / "home" / ".vibeskills" / "skill-roots.json", [str(shared_root)])
    _write_skill_roots_config(workspace_root / ".vibeskills" / "skill-roots.json", [str(shared_root)])

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="codex",
        agent_root=agent_root,
        workspace_root=workspace_root,
    )

    assert roots[0].root_key == "workspace_extra"
    assert [root.path for root in roots].count(shared_root.resolve()) == 1


def test_resolve_host_skill_roots_rejects_invalid_config_shape(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents" / "skills"
    config_path = tmp_path / "home" / ".vibeskills" / "skill-roots.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"schema_version": 1, "extra_skill_roots": "not-a-list"}', encoding="utf-8")

    with pytest.raises(ValueError, match="extra_skill_roots must be a list"):
        resolve_host_skill_roots(
            repo_root=REPO_ROOT,
            host_id="codex",
            agent_root=agent_root,
            workspace_root=None,
        )
