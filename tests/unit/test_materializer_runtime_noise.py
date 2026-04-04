from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"
for src in (CONTRACTS_SRC, INSTALLER_CORE_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.materializer import copy_dir_replace, copy_skill_roots_without_self_shadow


def test_copy_dir_replace_ignores_runtime_noise(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg" / "module.py").write_text("print(1)\n", encoding="utf-8")
    (src / "pkg" / "__pycache__").mkdir()
    (src / "pkg" / "__pycache__" / "module.cpython-310.pyc").write_bytes(b"pyc")
    (src / ".coverage").write_text("noise\n", encoding="utf-8")

    copy_dir_replace(src, dst)

    assert (dst / "pkg" / "module.py").exists()
    assert not (dst / "pkg" / "__pycache__").exists()
    assert not (dst / ".coverage").exists()


def test_copy_skill_roots_without_self_shadow_ignores_runtime_noise(tmp_path: Path) -> None:
    src = tmp_path / "skills-src"
    dst = tmp_path / "skills-dst"
    repo_root = tmp_path / "repo"
    skill_root = src / "example-skill"
    (skill_root / "nested").mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("---\nname: example-skill\ndescription: fixture\n---\n", encoding="utf-8")
    (skill_root / "nested" / "helper.py").write_text("print(1)\n", encoding="utf-8")
    (skill_root / "__pycache__").mkdir()
    (skill_root / "__pycache__" / "helper.cpython-310.pyc").write_bytes(b"pyc")

    copy_skill_roots_without_self_shadow(src, dst, repo_root)

    assert (dst / "example-skill" / "SKILL.md").exists()
    assert (dst / "example-skill" / "nested" / "helper.py").exists()
    assert not (dst / "example-skill" / "__pycache__").exists()
