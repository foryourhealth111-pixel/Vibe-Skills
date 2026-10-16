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


@pytest.mark.parametrize("scope", ["workspace", "user"])
def test_resolve_host_skill_roots_accepts_bom_config(tmp_path: Path, scope: str) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    base = workspace if scope == "workspace" else home
    config = base / ".vibeskills" / "skill-roots.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"schema_version": 1, "extra_skill_roots": ["team-skills"]}),
        encoding="utf-8-sig",
    )
    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT,
        host_id="codex",
        agent_root=home / ".agents" / "skills",
        workspace_root=workspace,
    )
    assert roots[0].path == (base / "team-skills").resolve()
    assert roots[0].root_key == scope + "_extra"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"schema_version": 2, "extra_skill_roots": []}', "schema_version must be 1"),
        ('{"schema_version": 1, "extra_skill_roots": [null]}', "non-empty strings"),
        ('{"schema_version": 1, "extra_skill_roots": ', "Expecting value"),
    ],
)
def test_bom_config_preserves_strict_validation(tmp_path: Path, content: str, message: str) -> None:
    workspace = tmp_path / "workspace"
    config = workspace / ".vibeskills" / "skill-roots.json"
    config.parent.mkdir(parents=True)
    config.write_text(content, encoding="utf-8-sig")
    with pytest.raises(ValueError, match=message):
        resolve_host_skill_roots(
            repo_root=REPO_ROOT,
            host_id="codex",
            agent_root=tmp_path / "home" / ".agents" / "skills",
            workspace_root=workspace,
        )


@pytest.mark.skipif(sys.platform == "win32", reason="Requires case-sensitive path identity")
def test_case_distinct_configured_skill_roots_remain_discoverable(tmp_path: Path) -> None:
    from vgo_runtime.kernel.skill_index import build_skill_index

    agent_root = tmp_path / "home/.agents/skills"
    workspace_root = tmp_path / "workspace"
    for root_name, skill_id in [("TeamSkills", "upper-report"), ("teamskills", "lower-report")]:
        skill_file = workspace_root / root_name / skill_id / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(
            f"---\nname: {skill_id}\ndescription: Produce a report.\n---\n", encoding="utf-8",
        )
    assert not (workspace_root / "TeamSkills").samefile(workspace_root / "teamskills")
    _write_skill_roots_config(
        workspace_root / ".vibeskills/skill-roots.json", ["TeamSkills", "teamskills"],
    )

    roots = resolve_host_skill_roots(
        repo_root=REPO_ROOT, host_id="codex", agent_root=agent_root, workspace_root=workspace_root,
    )
    index = build_skill_index(agent_root, host_roots=tuple(root.path for root in roots))

    assert {entry["skill_id"] for entry in index["skills"]} == {"upper-report", "lower-report"}
    assert [root.path for root in roots[:2]] == [
        (workspace_root / "TeamSkills").resolve(), (workspace_root / "teamskills").resolve(),
    ]
