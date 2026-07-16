from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel.skill_index import build_skill_catalog, build_skill_index


def _write_skill(skill_dir: Path, *, name: str, description: str) -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"""---
name: {name}
description: {description}
---
# {name}
""",
        encoding="utf-8",
    )
    return skill_file


def test_build_skill_catalog_collects_host_installed_and_vibe_local_entries(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    host_root = tmp_path / "host-skills"
    host_skill = _write_skill(
        host_root / "external-debugger",
        name="External Debugger",
        description="Read local debugging guidance from the host skill root.",
    )
    local_skill = _write_skill(
        vibe_root / "skills" / "local" / "code-review",
        name="Code Review",
        description="Review implementation risk.",
    )

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(host_root,))

    assert catalog["schema_version"] == "local_skill_index_v2"
    assert catalog["catalog_source_kinds"] == ["host_installed", "vibe_local"]
    assert catalog["active_source_kinds"] == ["host_installed", "vibe_local"]
    assert catalog["catalog_source_roots"] == [
        {
            "source_kind": "host_installed",
            "source_root": str(host_root.resolve()),
            "resolved_source_root": str(host_root.resolve()),
            "source_priority": 0,
            "source_order": 0,
        },
        {
            "source_kind": "vibe_local",
            "source_root": "skills/local",
            "resolved_source_root": str((vibe_root / "skills" / "local").resolve()),
            "source_priority": 1,
            "source_order": 1,
        },
    ]
    assert [entry["skill_id"] for entry in catalog["entries"]] == ["external-debugger", "code-review"]
    assert [entry["source_kind"] for entry in catalog["entries"]] == ["host_installed", "vibe_local"]
    assert [entry["skill_entrypoint"] for entry in catalog["entries"]] == [
        str(host_skill.resolve()),
        str(local_skill.resolve()),
    ]
    assert [entry["active"] for entry in catalog["entries"]] == [True, True]


def test_build_skill_catalog_marks_duplicates_inactive_by_root_order(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    first_host_root = tmp_path / "host-skills-a"
    second_host_root = tmp_path / "host-skills-b"
    first_skill = _write_skill(first_host_root / "shared-skill", name="First Skill", description="First root wins.")
    second_skill = _write_skill(second_host_root / "shared-skill", name="Second Skill", description="Second root loses.")

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(first_host_root, second_host_root))
    rows = catalog["entries"]

    assert [row["display_name"] for row in rows] == ["First Skill", "Second Skill"]
    assert [row["source_order"] for row in rows] == [0, 1]
    assert [row["active"] for row in rows] == [True, False]
    assert [row["duplicate_state"] for row in rows] == ["active", "shadowed_duplicate"]
    assert catalog["discovery_diagnostics"]["duplicates"] == [
        {
            "skill_id": "shared-skill",
            "active_entrypoint": str(first_skill.resolve()),
            "inactive_entrypoints": [str(second_skill.resolve())],
            "resolution": "first_root_wins",
        }
    ]


def test_build_skill_catalog_uses_directory_skill_ids_for_host_entries(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    host_root = tmp_path / "host-skills"
    frontmatter = """---
id: shared
name: Shared Skill
description: Same declared id in one root.
---
# Shared
"""
    first_skill = host_root / "one" / "SKILL.md"
    second_skill = host_root / "two" / "SKILL.md"
    first_skill.parent.mkdir(parents=True)
    second_skill.parent.mkdir(parents=True)
    first_skill.write_text(frontmatter, encoding="utf-8")
    second_skill.write_text(frontmatter, encoding="utf-8")

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(host_root,))

    assert [row["skill_id"] for row in catalog["entries"]] == ["one", "two"]
    assert [row["skill_entrypoint"] for row in catalog["entries"]] == [
        str(first_skill.resolve()),
        str(second_skill.resolve()),
    ]
    assert [row["active"] for row in catalog["entries"]] == [True, True]
    assert catalog["discovery_diagnostics"]["duplicates"] == []


def test_build_skill_index_includes_active_host_installed_skill_when_host_roots_exist(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    host_root = tmp_path / "host-skills"
    skill_path = _write_skill(
        host_root / "external-debugger",
        name="External Debugger",
        description="Read local debugging guidance from the host skill root.",
    )

    payload = build_skill_index(agent_root, host_roots=(host_root,))

    assert payload["roots"] == [str(host_root.resolve())]
    assert payload["catalog_source_kinds"] == ["host_installed"]
    assert payload["active_source_kinds"] == ["host_installed"]
    assert [entry["skill_id"] for entry in payload["skills"]] == ["external-debugger"]
    assert payload["skills"][0]["source_kind"] == "host_installed"
    assert payload["skills"][0]["skill_entrypoint"] == str(skill_path.resolve())
