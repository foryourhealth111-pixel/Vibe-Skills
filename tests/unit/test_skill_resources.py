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
