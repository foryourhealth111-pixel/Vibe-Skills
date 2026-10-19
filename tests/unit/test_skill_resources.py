from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages/runtime-core/src"))

from vgo_runtime.kernel.skill_resources import SkillResourceError, skill_resource_sha256


def _link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


def test_contained_link_tracks_resource_content_and_target(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(b"Skill descriptor")
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "rule.txt").write_text("Same rule", encoding="utf-8")
    (second / "rule.txt").write_text("Same rule", encoding="utf-8")
    link = tmp_path / "rules"
    _link(link, first)
    original = skill_resource_sha256(skill, skill.read_bytes())
    link.unlink()
    _link(link, second)
    retargeted = skill_resource_sha256(skill, skill.read_bytes())
    assert retargeted != original
    (second / "rule.txt").write_text("Updated rule", encoding="utf-8")
    assert skill_resource_sha256(skill, skill.read_bytes()) != retargeted


@pytest.mark.parametrize("kind", ["external", "cycle"])
def test_resource_links_require_containment_and_acyclic_directories(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "skill"
    root.mkdir()
    skill = root / "SKILL.md"
    skill.write_bytes(b"Skill descriptor")
    target = tmp_path if kind == "external" else root
    _link(root / "linked", target)
    with pytest.raises(SkillResourceError, match="escapes|Cyclic"):
        skill_resource_sha256(skill, skill.read_bytes())


@pytest.mark.parametrize("environment_name", [".venv", "venv", ".env", "env", "custom-environment"])
def test_virtualenv_resources_are_pruned_before_traversal(tmp_path: Path, monkeypatch, environment_name: str) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(b"Skill descriptor")
    script = tmp_path / "scripts/run.py"
    script.parent.mkdir()
    script.write_text("print('first')", encoding="utf-8")
    original = skill_resource_sha256(skill, skill.read_bytes())
    environment = script.parent / environment_name
    environment.mkdir()
    if environment_name == "custom-environment":
        (environment / "pyvenv.cfg").write_text("home = /system/python\n", encoding="utf-8")
    (environment / "generated.py").write_text("generated dependency", encoding="utf-8")
    iterdir = Path.iterdir

    def guarded_iterdir(path):
        assert path != environment, "Resource scans must prune virtual environments before traversal"
        return iterdir(path)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    assert skill_resource_sha256(skill, skill.read_bytes()) == original
    (environment / "generated.py").write_text("updated dependency", encoding="utf-8")
    assert skill_resource_sha256(skill, skill.read_bytes()) == original
    script.write_text("print('updated')", encoding="utf-8")
    assert skill_resource_sha256(skill, skill.read_bytes()) != original


def test_virtualenv_interpreter_link_preserves_skill_catalog_admission(tmp_path: Path) -> None:
    from vgo_runtime.kernel.skill_index import scan_skill_catalog

    root = tmp_path / "agent"
    host_root = tmp_path / "host-skills"
    skill = host_root / "documents/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: documents\ndescription: Render formal documents.\n---\n", encoding="utf-8")
    original = scan_skill_catalog(agent_root=root, host_roots=(host_root,))
    assert [entry["skill_id"] for entry in original["entries"]] == ["documents"]
    environment = skill.parent / "scripts/custom-environment"
    (environment / "bin").mkdir(parents=True)
    (environment / "pyvenv.cfg").write_text("home = /system/python\n", encoding="utf-8")
    interpreter = tmp_path / "system-python"
    interpreter.write_bytes(b"System interpreter")
    _link(environment / "bin/python", interpreter)
    catalog = scan_skill_catalog(agent_root=root, host_roots=(host_root,))
    assert catalog["entries"] == original["entries"]
    assert catalog["discovery_diagnostics"]["invalid_entries"] == []
