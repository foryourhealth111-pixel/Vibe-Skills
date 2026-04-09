from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "_repo.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("vgo_verify_repo_unit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_repo_root_prefers_nearest_governed_git_root_for_worktree_like_layout(tmp_path: Path) -> None:
    module = _load_module()
    outer_root = tmp_path / "outer-repo"
    worktree_root = outer_root / ".worktrees" / "feature-a"
    script_path = worktree_root / "scripts" / "verify" / "runtime_neutral" / "freshness_gate.py"

    (outer_root / "config").mkdir(parents=True, exist_ok=True)
    (outer_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
    (outer_root / ".git").mkdir(parents=True, exist_ok=True)

    (worktree_root / "config").mkdir(parents=True, exist_ok=True)
    (worktree_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
    (worktree_root / ".git").write_text("gitdir: /tmp/fake-worktree-git\n", encoding="utf-8")

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    resolved = module.resolve_repo_root(script_path)

    assert resolved == worktree_root.resolve()
