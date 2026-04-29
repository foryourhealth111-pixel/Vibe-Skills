from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_support.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("router_contract_support_unit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_skill_md_path_prefers_hidden_internal_corpus_for_specialist(tmp_path: Path) -> None:
    module = _load_module()
    repo = module.RepoContext(
        repo_root=REPO_ROOT,
        config_root=REPO_ROOT / "config",
        bundled_skills_root=REPO_ROOT / "bundled" / "skills",
    )
    hidden_root = tmp_path / "skills" / "vibe" / "bundled" / "skills" / "scikit-learn"
    public_root = tmp_path / "skills" / "scikit-learn"
    hidden_root.mkdir(parents=True, exist_ok=True)
    public_root.mkdir(parents=True, exist_ok=True)
    hidden_descriptor = hidden_root / "SKILL.runtime-mirror.md"
    public_descriptor = public_root / "SKILL.md"
    hidden_descriptor.write_text("---\nname: scikit-learn\n---\n", encoding="utf-8")
    public_descriptor.write_text("---\nname: scikit-learn\ndescription: public shadow\n---\n", encoding="utf-8")

    resolved = module.resolve_skill_md_path(repo, "scikit-learn", str(tmp_path), "codex")

    assert resolved == hidden_descriptor


def test_resolve_skill_md_path_uses_canonical_vibe_entrypoint(tmp_path: Path) -> None:
    module = _load_module()
    repo = module.RepoContext(
        repo_root=REPO_ROOT,
        config_root=REPO_ROOT / "config",
        bundled_skills_root=REPO_ROOT / "bundled" / "skills",
    )
    vibe_root = tmp_path / "skills" / "vibe"
    vibe_root.mkdir(parents=True, exist_ok=True)
    descriptor = vibe_root / "SKILL.md"
    descriptor.write_text("---\nname: vibe\ndescription: governed runtime\n---\n", encoding="utf-8")

    resolved = module.resolve_skill_md_path(repo, "vibe", str(tmp_path), "codex")
    metadata = module.read_skill_descriptor(repo, "vibe", str(tmp_path), "codex")

    assert resolved == descriptor
    assert metadata["skill_md_path"] == str(descriptor)
    assert metadata["description"] == "governed runtime"


def test_resolve_repo_root_prefers_nearest_config_root_without_git(tmp_path: Path) -> None:
    module = _load_module()
    target_root = tmp_path / "target"
    installed_root = target_root / "skills" / "vibe"
    script_path = installed_root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"

    (target_root / "config").mkdir(parents=True, exist_ok=True)
    (target_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
    (installed_root / "config").mkdir(parents=True, exist_ok=True)
    (installed_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("# runtime\n", encoding="utf-8")

    resolved = module.resolve_repo_root(script_path)

    assert resolved == installed_root


def test_resolve_repo_root_prefers_nearest_governed_git_root_for_worktrees(tmp_path: Path) -> None:
    module = _load_module()
    outer_root = tmp_path / "repo"
    worktree_root = outer_root / ".worktrees" / "feature"
    script_path = worktree_root / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_bridge.py"

    outer_root.mkdir(parents=True, exist_ok=True)
    (outer_root / ".git").mkdir(parents=True, exist_ok=True)
    (outer_root / "config").mkdir(parents=True, exist_ok=True)
    (outer_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")

    worktree_root.mkdir(parents=True, exist_ok=True)
    (worktree_root / ".git").write_text("gitdir: ../../.git/worktrees/feature\n", encoding="utf-8")
    (worktree_root / "config").mkdir(parents=True, exist_ok=True)
    (worktree_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("# router bridge\n", encoding="utf-8")

    resolved = module.resolve_repo_root(script_path)

    assert resolved == worktree_root


def test_keyword_hit_ignores_keywords_only_present_in_negated_scope() -> None:
    module = _load_module()
    prompt = "帮我整理电子实验记录 ELN 模板，不指定 Benchling 或 LabArchives".casefold()

    assert module.keyword_hit(prompt, "benchling") is False
    assert module.keyword_hit(prompt, "labarchives") is False


def test_keyword_hit_keeps_positive_keyword_outside_negated_scope() -> None:
    module = _load_module()
    prompt = "用 Opentrons 写 protocol，不使用 Benchling 或 LabArchives".casefold()

    assert module.keyword_hit(prompt, "opentrons") is True
    assert module.keyword_hit(prompt, "benchling") is False


def test_keyword_hit_keeps_explicit_negative_phrase_matchable() -> None:
    module = _load_module()
    prompt = "写一个普通 wet-lab protocol 的 Markdown 文档，不使用 protocols.io 或机器人".casefold()

    assert module.keyword_hit(prompt, "protocols.io") is False
    assert module.keyword_hit(prompt, "不使用 protocols.io") is True


def test_resolve_target_root_defaults_codex_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="codex")

    assert resolved == (tmp_path / ".codex").resolve()


def test_resolve_target_root_defaults_claude_code_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("CLAUDE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="claude-code")

    assert resolved == (tmp_path / ".claude").resolve()


def test_resolve_target_root_defaults_cursor_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("CURSOR_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="cursor")

    assert resolved == (tmp_path / ".cursor").resolve()


def test_resolve_target_root_defaults_windsurf_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("WINDSURF_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="windsurf")

    assert resolved == (tmp_path / ".codeium" / "windsurf").resolve()


def test_resolve_target_root_defaults_openclaw_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="openclaw")

    assert resolved == (tmp_path / ".openclaw").resolve()


def test_resolve_target_root_defaults_opencode_to_real_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.delenv("OPENCODE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)

    resolved = module.resolve_target_root(host_id="opencode")

    assert resolved == (tmp_path / ".config" / "opencode").resolve()
