from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / "packages" / "contracts" / "src"
INSTALLER_SRC = ROOT / "packages" / "installer-core" / "src"
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.simple_skill_installer import (
    check_vibe_skill,
    install_vibe_skill,
    uninstall_vibe_skill,
    update_vibe_skill,
)


def _write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_runtime_contract(
    repo_root: Path,
    *,
    config_files: tuple[str, ...] = (),
    script_files: tuple[str, ...] = (),
    package_dirs: tuple[str, ...] = (),
) -> None:
    _write(
        repo_root / "config" / "version-governance.json",
        json.dumps(
            {
                "packaging": {
                    "runtime_payload": {
                        "files": [
                            "SKILL.md",
                            "core/skill-contracts/v1/vibe.json",
                            "config/runtime-config-manifest.json",
                            "config/runtime-script-manifest.json",
                        ],
                        "directories": ["protocols"],
                    },
                    "manifests": [
                        {"id": "runtime_scripts", "path": "config/runtime-script-manifest.json"},
                        {"id": "runtime_configs", "path": "config/runtime-config-manifest.json"},
                    ],
                }
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        repo_root / "config" / "runtime-config-manifest.json",
        json.dumps({"files": list(config_files), "directories": []}, indent=2) + "\n",
    )
    _write(
        repo_root / "config" / "runtime-script-manifest.json",
        json.dumps({"files": list(script_files), "directories": list(package_dirs)}, indent=2) + "\n",
    )
    _write(
        repo_root / "core" / "skill-contracts" / "v1" / "vibe.json",
        json.dumps({"id": "vibe"}, indent=2) + "\n",
    )


def test_install_copies_only_the_simplified_vibe_package(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    for relpath in (
        "SKILL.md",
        "config/runtime.json",
        "protocols/runtime.md",
        "apps/vgo-cli/src/vgo_cli/main.py",
        "apps/vgo-cli/src/vgo_cli/upgrade_service.py",
        "apps/vgo-cli/src/vgo_cli/install_support.py",
        "apps/vgo-cli/src/vgo_cli/install_gates.py",
        "apps/vgo-cli/src/vgo_cli/installer_bridge.py",
        "apps/vgo-cli/src/vgo_cli/__pycache__/main.cpython-310.pyc",
        "packages/contracts/src/vgo_contracts/__init__.py",
        "packages/runtime-core/src/vgo_runtime/__init__.py",
        "packages/runtime-core/src/vgo_runtime/test_skill_cache_routing.py",
        "packages/verification-core/src/vgo_verify/__init__.py",
        "packages/verification-core/src/vgo_verify/runtime_delivery_acceptance.py",
        "packages/verification-core/src/vgo_verify/test_baseline_audit.py",
        "packages/verification-core/src/vgo_verify/test_runtime_delivery_acceptance_lock_reconciliation.py",
        "adapters/index.json",
        "scripts/common/vibe-governance-helpers.ps1",
        "scripts/runtime/VibeRuntime.Common.ps1",
        "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
    ):
        _write(repo_root / relpath)
    for relpath in (
        "agents/openai.yaml",
        "commands/vibe.md",
        "docs/install/README.md",
        "dist/archive.zip",
        "bundled/skills/brainstorming/SKILL.md",
        "tests/unit/test_old.py",
        "outputs/runtime/log.txt",
        ".vibeskills/install-ledger.json",
    ):
        _write(repo_root / relpath)
    _seed_runtime_contract(
        repo_root,
        config_files=("config/runtime.json",),
        script_files=(
            "scripts/common/vibe-governance-helpers.ps1",
            "scripts/runtime/VibeRuntime.Common.ps1",
            "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
        ),
        package_dirs=(
            "apps/vgo-cli",
            "packages/contracts",
            "packages/runtime-core",
            "packages/verification-core",
        ),
    )

    receipt = install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=True,
    )

    install_root = skills_dir / "vibe"
    assert (install_root / "SKILL.md").is_file()
    assert (install_root / "config/runtime.json").is_file()
    assert (install_root / "protocols/runtime.md").is_file()
    assert not (install_root / "adapters").exists()
    assert not (install_root / "config/pack-manifest.json").exists()
    assert not (install_root / "config/role-pack-policy.json").exists()
    assert not (install_root / "config/bundled-skill-governance-policy.json").exists()
    assert not (install_root / "apps" / "vgo-cli" / "src" / "vgo_cli" / "upgrade_service.py").exists()
    assert not (install_root / "apps" / "vgo-cli" / "src" / "vgo_cli" / "install_support.py").exists()
    assert not (install_root / "apps" / "vgo-cli" / "src" / "vgo_cli" / "install_gates.py").exists()
    assert not (install_root / "apps" / "vgo-cli" / "src" / "vgo_cli" / "installer_bridge.py").exists()
    assert not (install_root / "apps" / "vgo-cli" / "src" / "vgo_cli" / "__pycache__").exists()
    assert not (install_root / "packages" / "runtime-core" / "src" / "vgo_runtime" / "test_skill_cache_routing.py").exists()
    assert (install_root / "packages" / "verification-core" / "src" / "vgo_verify" / "runtime_delivery_acceptance.py").is_file()
    assert (install_root / "packages" / "verification-core" / "src" / "vgo_verify" / "test_baseline_audit.py").is_file()
    assert not (install_root / "packages" / "verification-core" / "src" / "vgo_verify" / "test_runtime_delivery_acceptance_lock_reconciliation.py").exists()
    assert not (install_root / "packages" / "verification-core" / "src" / "vgo_verify" / "global_pack_consolidation_audit.py").exists()
    assert (install_root / "scripts" / "common" / "vibe-governance-helpers.ps1").is_file()
    assert (install_root / "scripts" / "verify" / "vibe-release-install-runtime-coherence-gate.ps1").is_file()
    assert not (install_root / "scripts" / "verify" / "vibe-pack-routing-smoke.ps1").exists()
    assert not (install_root / "docs").exists()
    assert not (install_root / "tests").exists()
    assert not (install_root / "bundled").exists()
    assert receipt["receipt_kind"] == "vibe-skill-install"
    assert receipt["skill_id"] == "vibe"
    assert receipt["install_root"] == str(install_root.resolve())
    assert receipt["source_git_commit"] == "abc123"
    assert receipt["source_git_dirty"] is True
    assert any(entry["path"] == "SKILL.md" for entry in receipt["files"])
    assert (install_root / ".vibeskills" / "install-receipt.json").is_file()


def test_install_public_release_writes_release_identity_not_git_fields(tmp_path: Path) -> None:
    repo_root = tmp_path / "release-root"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    receipt = install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-08T08:00:00Z",
        source_kind="public_release",
        release_version="3.2.0",
        release_asset_name="vibe-skills-3.2.0-public.zip",
        release_asset_digest="release-digest-123",
    )

    assert receipt["source_kind"] == "public_release"
    assert receipt["release"] == {
        "version": "3.2.0",
        "asset_name": "vibe-skills-3.2.0-public.zip",
        "asset_digest_sha256": "release-digest-123",
    }
    assert "source_git_commit" not in receipt
    assert "source_git_dirty" not in receipt


def test_check_reports_drift_when_receipt_owned_file_changes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )

    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True

    (skills_dir / "vibe" / "SKILL.md").write_text("# changed\n", encoding="utf-8")
    result = check_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["drifted_files"] == ["SKILL.md"]


def test_update_refuses_to_overwrite_drifted_install(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    (skills_dir / "vibe" / "SKILL.md").write_text("# local edit\n", encoding="utf-8")

    try:
        update_vibe_skill(
            repo_root=next_repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
            source_git_commit="def456",
            source_git_dirty=False,
        )
    except RuntimeError as exc:
        assert "drift" in str(exc)
    else:
        raise AssertionError("update should refuse a drifted install")

    assert (skills_dir / "vibe" / "SKILL.md").read_text(encoding="utf-8") == "# local edit\n"


def test_update_preserves_user_added_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    user_file = skills_dir / "vibe" / "notes.md"
    user_file.write_text("keep me\n", encoding="utf-8")

    receipt = update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
        source_git_commit="def456",
        source_git_dirty=False,
    )

    assert (skills_dir / "vibe" / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"
    assert user_file.read_text(encoding="utf-8") == "keep me\n"
    assert "notes.md" not in {entry["path"] for entry in receipt["files"]}


def test_install_rerun_preserves_user_added_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    user_file = skills_dir / "vibe" / "notes.md"
    user_file.write_text("keep me\n", encoding="utf-8")

    receipt = install_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
        source_git_commit="def456",
        source_git_dirty=False,
    )

    assert (skills_dir / "vibe" / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"
    assert user_file.read_text(encoding="utf-8") == "keep me\n"
    assert "notes.md" not in {entry["path"] for entry in receipt["files"]}


def test_check_reports_user_added_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    (skills_dir / "vibe" / "notes.md").write_text("keep me\n", encoding="utf-8")

    result = check_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is True
    assert result["extra_files"] == ["notes.md"]


def test_uninstall_removes_owned_files_but_keeps_user_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    user_file = skills_dir / "vibe" / "notes.md"
    user_file.write_text("keep me\n", encoding="utf-8")

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    removed_files = set(result["removed_files"])
    assert "SKILL.md" in removed_files
    assert "config/runtime-config-manifest.json" in removed_files
    assert "config/runtime-script-manifest.json" in removed_files
    assert user_file.read_text(encoding="utf-8") == "keep me\n"
    assert (skills_dir / "vibe").is_dir()
