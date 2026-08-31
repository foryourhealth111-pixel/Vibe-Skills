from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap
import time

import pytest


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
import vgo_installer.simple_skill_installer as simple_skill_installer


def _write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _symlink_or_skip(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symbolic links are unavailable: {exc}")


def _junction_or_skip(link: Path, target: Path) -> None:
    if os.name != "nt":
        pytest.skip("directory junctions are Windows-only")
    target.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"directory junctions are unavailable: {result.stderr.strip()}")


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _run_install_until_process_exit(
    *,
    repo_root: Path,
    skills_dir: Path,
    exit_after_destination: Path,
) -> None:
    script = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import sys

        import vgo_installer.simple_skill_installer as installer

        repo_root = Path(sys.argv[1])
        skills_dir = Path(sys.argv[2])
        exit_after_destination = Path(sys.argv[3]).resolve(strict=False)
        original_replace = installer.os.replace

        def replace_then_exit(source, destination):
            original_replace(source, destination)
            if Path(destination).resolve(strict=False) == exit_after_destination:
                os._exit(91)

        installer.os.replace = replace_then_exit
        installer.install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
        )
        """
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        path
        for path in (
            str(CONTRACTS_SRC),
            str(INSTALLER_SRC),
            environment.get("PYTHONPATH", ""),
        )
        if path
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(repo_root),
            str(skills_dir),
            str(exit_after_destination),
        ],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=10,
    )
    assert result.returncode == 91, result.stderr


def _run_install_until_staging_exit(*, repo_root: Path, skills_dir: Path) -> None:
    script = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import sys

        import vgo_installer.simple_skill_installer as installer

        repo_root = Path(sys.argv[1])
        skills_dir = Path(sys.argv[2])
        original_copy = installer.shutil.copy2

        def copy_then_exit(source, destination):
            result = original_copy(source, destination)
            if Path(source).name == "SKILL.md":
                os._exit(92)
            return result

        installer.shutil.copy2 = copy_then_exit
        installer.install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
        )
        """
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        path
        for path in (
            str(CONTRACTS_SRC),
            str(INSTALLER_SRC),
            environment.get("PYTHONPATH", ""),
        )
        if path
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(repo_root), str(skills_dir)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=10,
    )
    assert result.returncode == 92, result.stderr


def _run_uninstall_until_state_delete_exit(*, skills_dir: Path) -> None:
    script = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import sys

        import vgo_installer.simple_skill_installer as installer

        skills_dir = Path(sys.argv[1])
        state_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
        original_unlink = Path.unlink

        def unlink_then_exit(path, *, missing_ok=False):
            original_unlink(path, missing_ok=missing_ok)
            if path == state_path:
                os._exit(93)

        Path.unlink = unlink_then_exit
        installer.uninstall_vibe_skill(skills_dir=skills_dir)
        """
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        path
        for path in (
            str(CONTRACTS_SRC),
            str(INSTALLER_SRC),
            environment.get("PYTHONPATH", ""),
        )
        if path
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(skills_dir)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=10,
    )
    assert result.returncode == 93, result.stderr


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


def test_invalid_public_release_identity_does_not_create_install_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "release-root"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    with pytest.raises(RuntimeError, match="requires release version and asset name"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-08T08:00:00Z",
            source_kind="public_release",
            release_version="",
            release_asset_name="",
        )

    assert not (skills_dir / "vibe").exists()


def test_install_rejects_packaging_path_that_escapes_install_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    def escaping_relpaths(source_root: Path) -> list[str]:
        assert source_root == repo_root.resolve()
        return ["config/../../escaped.txt"]

    monkeypatch.setattr(
        simple_skill_installer,
        "_package_file_relpaths",
        escaping_relpaths,
    )

    with pytest.raises(RuntimeError, match="Install path escapes the Vibe install root"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
            source_git_commit="abc123",
            source_git_dirty=False,
        )

    assert not (skills_dir / "escaped.txt").exists()


def test_install_rejects_junction_install_root_that_targets_outside_skills_dir(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    outside_root = tmp_path / "outside"
    install_root = skills_dir / "vibe"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    skills_dir.mkdir(parents=True)
    _junction_or_skip(install_root, outside_root)

    try:
        with pytest.raises(RuntimeError, match="symbolic link or junction"):
            install_vibe_skill(
                repo_root=repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T08:00:00Z",
            )

        assert not list(outside_root.iterdir())
    finally:
        if install_root.exists():
            install_root.rmdir()


def test_install_rejects_packaging_source_that_escapes_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(tmp_path / "escaped.txt", "outside source\n")
    _seed_runtime_contract(
        repo_root,
        config_files=("config/../../escaped.txt",),
    )

    expected_error = (
        f"Unsafe package path in {repo_root / 'config' / 'version-governance.json'}: "
        "config/../../escaped.txt"
    )
    with pytest.raises(RuntimeError, match=re.escape(expected_error)):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
            source_git_commit="abc123",
            source_git_dirty=False,
        )

    assert not (skills_dir / "escaped.txt").exists()


def test_install_accepts_windows_style_packaging_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(repo_root / "config" / "runtime.json", '{"ok": true}\n')
    _seed_runtime_contract(repo_root, config_files=("config/runtime.json",))
    governance_path = repo_root / "config" / "version-governance.json"
    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    packaging = governance["packaging"]
    runtime_payload = packaging["runtime_payload"]
    runtime_payload["files"] = [path.replace("/", "\\") for path in runtime_payload["files"]]
    runtime_payload["directories"] = [
        path.replace("/", "\\") for path in runtime_payload["directories"]
    ]
    for manifest in packaging["manifests"]:
        manifest["path"] = manifest["path"].replace("/", "\\")
    _write(governance_path, json.dumps(governance, indent=2) + "\n")

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )

    assert (skills_dir / "vibe" / "config" / "runtime.json").is_file()


def test_install_allows_source_symlink_that_resolves_inside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    linked_source = repo_root / "shared" / "runtime.json"
    package_path = repo_root / "config" / "linked-runtime.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(linked_source, '{"safe": true}\n')
    _seed_runtime_contract(repo_root, config_files=("config/linked-runtime.json",))
    _symlink_or_skip(package_path, linked_source)

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )

    assert (skills_dir / "vibe" / "config" / "linked-runtime.json").read_text(
        encoding="utf-8"
    ) == '{"safe": true}\n'


def test_install_rejects_source_symlink_that_escapes_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    outside_source = tmp_path / "outside.json"
    package_path = repo_root / "config" / "linked-runtime.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(outside_source, '{"unsafe": true}\n')
    _seed_runtime_contract(repo_root, config_files=("config/linked-runtime.json",))
    _symlink_or_skip(package_path, outside_source)

    with pytest.raises(RuntimeError, match="Package path escapes the source root"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
        )

    assert not (skills_dir / "vibe" / "config" / "linked-runtime.json").exists()


def test_install_rejects_packaging_manifest_that_escapes_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "nested" / "repo"
    skills_dir = tmp_path / "skills"
    outside_manifest = tmp_path / "outside.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(outside_manifest, json.dumps({"files": ["SKILL.md"]}) + "\n")
    _write(
        repo_root / "config" / "version-governance.json",
        json.dumps(
            {
                "packaging": {
                    "runtime_payload": {"files": ["SKILL.md"], "directories": []},
                    "manifests": [{"id": "outside", "path": "../../outside.json"}],
                }
            }
        )
        + "\n",
    )

    with pytest.raises(RuntimeError, match="Unsafe package manifest path"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
        )

    assert outside_manifest.read_text(encoding="utf-8") == '{"files": ["SKILL.md"]}\n'


def test_install_rejects_non_object_runtime_governance(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "config" / "version-governance.json", "[]\n")

    with pytest.raises(RuntimeError, match="Expected JSON object"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
        )


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


def test_check_reports_owned_leaf_symlink_as_drift(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    external_file = tmp_path / "external-skill.md"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(external_file, "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    installed_skill = skills_dir / "vibe" / "SKILL.md"
    installed_skill.unlink()
    _symlink_or_skip(installed_skill, external_file)

    result = check_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["drifted_files"] == ["SKILL.md"]
    assert external_file.read_text(encoding="utf-8") == "# vibe\n"


def test_check_detects_owned_file_replaced_by_symlink_before_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    external_file = tmp_path / "external-skill.md"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(external_file, "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    installed_skill = skills_dir / "vibe" / "SKILL.md"
    original_link_check = simple_skill_installer._path_is_link_or_reparse_point
    swapped = False

    def swap_after_link_check(path: Path) -> bool:
        nonlocal swapped
        result = original_link_check(path)
        if path == installed_skill and not swapped:
            installed_skill.unlink()
            _symlink_or_skip(installed_skill, external_file)
            swapped = True
        return result

    monkeypatch.setattr(
        simple_skill_installer,
        "_path_is_link_or_reparse_point",
        swap_after_link_check,
    )

    result = check_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["drifted_files"] == ["SKILL.md"]
    assert installed_skill.is_symlink()
    assert external_file.read_text(encoding="utf-8") == "# vibe\n"


def test_transaction_hash_rejects_file_replaced_by_symlink_after_precheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "installed.txt"
    external_file = tmp_path / "external.txt"
    _write(destination, "same contents\n")
    _write(external_file, "same contents\n")
    original_link_check = simple_skill_installer._path_is_link_or_reparse_point
    swapped = False

    def swap_after_link_check(path: Path) -> bool:
        nonlocal swapped
        result = original_link_check(path)
        if path == destination and not swapped:
            destination.unlink()
            _symlink_or_skip(destination, external_file)
            swapped = True
        return result

    monkeypatch.setattr(
        simple_skill_installer,
        "_path_is_link_or_reparse_point",
        swap_after_link_check,
    )

    expected_error = f"File changed to a symbolic link before hashing: {destination}"
    with pytest.raises(RuntimeError, match=re.escape(expected_error)):
        simple_skill_installer._current_install_file_sha256(
            destination,
            relpath="installed.txt",
        )

    assert destination.is_symlink()
    assert external_file.read_text(encoding="utf-8") == "same contents\n"


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are Windows-only")
def test_transaction_hash_rejects_junction_replacement_after_precheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "installed.txt"
    external_root = tmp_path / "external"
    external_file = external_root / "keep.txt"
    _write(destination, "managed contents\n")
    _write(external_file, "keep me\n")
    original_link_check = simple_skill_installer._path_is_link_or_reparse_point
    original_is_file = Path.is_file
    swapped = False

    def swap_after_link_check(path: Path) -> bool:
        nonlocal swapped
        result = original_link_check(path)
        if path == destination and not swapped:
            destination.unlink()
            _junction_or_skip(destination, external_root)
            swapped = True
        return result

    monkeypatch.setattr(
        simple_skill_installer,
        "_path_is_link_or_reparse_point",
        swap_after_link_check,
    )

    def report_raced_path_as_file(path: Path) -> bool:
        if path == destination and swapped:
            return True
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", report_raced_path_as_file)

    expected_error = (
        f"File changed to a link, junction, or non-file before hashing: {destination}"
    )
    with pytest.raises(RuntimeError, match=re.escape(expected_error)):
        simple_skill_installer._current_install_file_sha256(
            destination,
            relpath="installed.txt",
        )

    assert destination.is_dir()
    assert external_file.read_text(encoding="utf-8") == "keep me\n"
    destination.rmdir()


def test_check_missing_install_does_not_create_skills_directory(tmp_path: Path) -> None:
    skills_dir = tmp_path / "missing-skills"

    result = check_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert Path(str(result["missing_receipt"])) == (
        skills_dir.resolve() / "vibe" / ".vibeskills" / "install-receipt.json"
    )
    assert not skills_dir.exists()


def test_operation_lock_rejects_hardlink_without_mutating_external_file(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    external_file = tmp_path / "external-lock"
    lock_path = skills_dir / ".vibeskills" / "vibe-operation.lock"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    external_file.touch()
    lock_path.parent.mkdir(parents=True)
    try:
        os.link(external_file, lock_path)
    except OSError as exc:
        pytest.skip(f"hard links are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="operation lock must not be a hard link"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
        )

    assert external_file.read_bytes() == b""


def test_platform_file_lock_propagates_non_contention_error_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "operation.lock"
    lock_path.write_bytes(b"\0")
    failure = OSError(errno.EIO, "lock I/O failure")

    def fail_lock(*args: object) -> None:
        raise failure

    if os.name == "nt":
        import msvcrt

        monkeypatch.setattr(msvcrt, "locking", fail_lock)
    else:
        import fcntl

        monkeypatch.setattr(fcntl, "flock", fail_lock)

    def fail_sleep(seconds: float) -> None:
        pytest.fail(f"non-contention lock failure slept for {seconds} seconds")

    monkeypatch.setattr(simple_skill_installer.time, "sleep", fail_sleep)
    with lock_path.open("r+b") as handle:
        with pytest.raises(OSError) as error:
            simple_skill_installer._acquire_platform_file_lock(
                handle.fileno(),
                lock_path,
            )

    assert error.value is failure


def test_platform_file_lock_times_out_for_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "operation.lock"
    lock_path.write_bytes(b"\0")

    def fail_lock(*args: object) -> None:
        raise PermissionError(errno.EACCES, "lock is held")

    if os.name == "nt":
        import msvcrt

        monkeypatch.setattr(msvcrt, "locking", fail_lock)
    else:
        import fcntl

        monkeypatch.setattr(fcntl, "flock", fail_lock)

    monkeypatch.setattr(simple_skill_installer, "OPERATION_LOCK_TIMEOUT_SECONDS", 0.0)
    with lock_path.open("r+b") as handle:
        with pytest.raises(TimeoutError, match="Timed out waiting"):
            simple_skill_installer._acquire_platform_file_lock(
                handle.fileno(),
                lock_path,
            )


def test_uninstall_rejects_receipt_root_mismatch_without_deleting_external_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    outside_root = tmp_path / "outside"
    victim = outside_root / "victim.txt"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(victim, "keep me\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    receipt_path = skills_dir / "vibe" / ".vibeskills" / "install-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["install_root"] = str(outside_root.resolve())
    receipt["files"] = [{"path": "victim.txt", "sha256": "fixture"}]
    _write(receipt_path, json.dumps(receipt, indent=2) + "\n")

    with pytest.raises(RuntimeError, match="install root mismatch"):
        uninstall_vibe_skill(skills_dir=skills_dir)

    assert victim.read_text(encoding="utf-8") == "keep me\n"
    assert receipt_path.is_file()


def test_uninstall_rejects_parent_path_in_receipt_without_deleting_external_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    victim = tmp_path / "victim.txt"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(victim, "keep me\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
        source_git_commit="abc123",
        source_git_dirty=False,
    )
    receipt_path = skills_dir / "vibe" / ".vibeskills" / "install-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"] = [{"path": "../../victim.txt", "sha256": "fixture"}]
    _write(receipt_path, json.dumps(receipt, indent=2) + "\n")

    with pytest.raises(RuntimeError, match="Unsafe owned file path"):
        uninstall_vibe_skill(skills_dir=skills_dir)

    assert victim.read_text(encoding="utf-8") == "keep me\n"
    assert receipt_path.is_file()


def test_uninstall_rejects_owned_path_through_parent_symlink(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    external_root = tmp_path / "external"
    external_file = external_root / "owned.txt"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(repo_root / "config" / "nested" / "owned.txt", "managed\n")
    _write(external_file, "keep me\n")
    _seed_runtime_contract(repo_root, config_files=("config/nested/owned.txt",))
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    installed_file = install_root / "config" / "nested" / "owned.txt"
    installed_file.unlink()
    installed_file.parent.rmdir()
    _symlink_or_skip(installed_file.parent, external_root)

    expected_error = f"Install path escapes the Vibe install root: {installed_file}"
    with pytest.raises(RuntimeError, match=re.escape(expected_error)):
        uninstall_vibe_skill(skills_dir=skills_dir)

    assert external_file.read_text(encoding="utf-8") == "keep me\n"
    assert (install_root / ".vibeskills" / "install-receipt.json").is_file()


def test_uninstall_removes_owned_leaf_symlink_and_preserves_external_target(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    external_file = tmp_path / "external-skill.md"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(external_file, "keep me\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    installed_skill = skills_dir / "vibe" / "SKILL.md"
    installed_skill.unlink()
    _symlink_or_skip(installed_skill, external_file)

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["status"] == "uninstalled"
    assert not installed_skill.exists()
    assert not installed_skill.is_symlink()
    assert external_file.read_text(encoding="utf-8") == "keep me\n"


@pytest.mark.parametrize(
    "owned_path",
    [
        ".vibeskills/install-receipt.json",
        ".vibeskills./install-receipt.json",
    ],
)
def test_uninstall_rejects_receipt_path_inside_installer_metadata(
    tmp_path: Path,
    owned_path: str,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    receipt_path = skills_dir / "vibe" / ".vibeskills" / "install-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"] = [{"path": owned_path, "sha256": "fixture"}]
    _write(receipt_path, json.dumps(receipt, indent=2) + "\n")

    with pytest.raises(RuntimeError, match="Unsafe owned file path"):
        uninstall_vibe_skill(skills_dir=skills_dir)

    assert receipt_path.is_file()


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


def test_update_copy_failure_keeps_existing_file_and_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    original_receipt = receipt_path.read_bytes()
    original_copy2 = simple_skill_installer.shutil.copy2
    copy_attempt = 0

    def fail_after_partial_copy(source: Path, destination: Path) -> str | Path:
        nonlocal copy_attempt
        copy_attempt += 1
        if copy_attempt == 2:
            destination.write_text("partial\n", encoding="utf-8")
            raise OSError(f"copy failed: {source}")
        return original_copy2(source, destination)

    monkeypatch.setattr(simple_skill_installer.shutil, "copy2", fail_after_partial_copy)

    with pytest.raises(OSError, match="copy failed"):
        update_vibe_skill(
            repo_root=next_repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
        )

    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# old vibe\n"
    assert receipt_path.read_bytes() == original_receipt
    assert not list(install_root.rglob("*.tmp"))


def test_update_replace_failure_rolls_back_all_files_and_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(repo_root / "config" / "retired.json", '{"old": true}\n')
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _write(next_repo_root / "config" / "replacement.json", '{"new": true}\n')
    _seed_runtime_contract(repo_root, config_files=("config/retired.json",))
    _seed_runtime_contract(next_repo_root, config_files=("config/replacement.json",))
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    original_snapshot = _file_snapshot(install_root)
    original_replace = simple_skill_installer.os.replace
    payload_replacements = 0

    def fail_second_payload_replace(source: Path, destination: Path) -> None:
        nonlocal payload_replacements
        destination_path = Path(destination)
        if install_root in destination_path.parents and destination_path != receipt_path:
            payload_replacements += 1
            if payload_replacements == 2:
                raise OSError(f"replace failed: {destination_path}")
        original_replace(source, destination)

    with monkeypatch.context() as context:
        context.setattr(simple_skill_installer.os, "replace", fail_second_payload_replace)
        with pytest.raises(OSError, match="replace failed"):
            update_vibe_skill(
                repo_root=next_repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T09:00:00Z",
            )

    assert _file_snapshot(install_root) == original_snapshot
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not list(install_root.rglob("*.tmp"))

    update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )

    assert (install_root / "config" / "replacement.json").is_file()
    assert not (install_root / "config" / "retired.json").exists()


def test_update_reports_retained_backup_when_rollback_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    installed_skill = install_root / "SKILL.md"
    original_replace = simple_skill_installer.os.replace
    payload_replacements = 0
    apply_failed = False

    def fail_apply_and_rollback(source: Path, destination: Path) -> None:
        nonlocal apply_failed, payload_replacements
        destination_path = Path(destination)
        if install_root in destination_path.parents:
            if not apply_failed:
                payload_replacements += 1
                if payload_replacements == 2:
                    apply_failed = True
                    raise OSError(f"apply failed: {destination_path}")
            elif destination_path == installed_skill:
                raise OSError(f"rollback failed: {destination_path}")
        original_replace(source, destination)

    with monkeypatch.context() as context:
        context.setattr(simple_skill_installer.os, "replace", fail_apply_and_rollback)
        with pytest.raises(OSError, match="rollback was incomplete") as error:
            update_vibe_skill(
                repo_root=next_repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T09:00:00Z",
            )

    retained_backups = list(install_root.glob(".SKILL.md.*.tmp"))
    assert len(retained_backups) == 1
    assert str(retained_backups[0]) in str(error.value)
    assert retained_backups[0].read_text(encoding="utf-8") == "# old vibe\n"


def test_update_receipt_commit_failure_rolls_back_payload_and_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    original_snapshot = _file_snapshot(install_root)
    original_replace = simple_skill_installer.os.replace
    receipt_commit_failed = False

    def fail_receipt_commit_once(source: Path, destination: Path) -> None:
        nonlocal receipt_commit_failed
        if Path(destination) == receipt_path and not receipt_commit_failed:
            receipt_commit_failed = True
            raise OSError(f"receipt commit failed: {destination}")
        original_replace(source, destination)

    with monkeypatch.context() as context:
        context.setattr(simple_skill_installer.os, "replace", fail_receipt_commit_once)
        with pytest.raises(OSError, match="receipt commit failed"):
            update_vibe_skill(
                repo_root=next_repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T09:00:00Z",
            )

    assert _file_snapshot(install_root) == original_snapshot
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not list(install_root.rglob("*.tmp"))

    update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )
    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"


def test_new_install_receipt_commit_failure_leaves_retryable_empty_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    original_replace = simple_skill_installer.os.replace
    receipt_commit_failed = False

    def fail_receipt_commit_once(source: Path, destination: Path) -> None:
        nonlocal receipt_commit_failed
        if Path(destination) == receipt_path and not receipt_commit_failed:
            receipt_commit_failed = True
            raise OSError(f"receipt commit failed: {destination}")
        original_replace(source, destination)

    with monkeypatch.context() as context:
        context.setattr(simple_skill_installer.os, "replace", fail_receipt_commit_once)
        with pytest.raises(OSError, match="receipt commit failed"):
            install_vibe_skill(
                repo_root=repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T08:00:00Z",
            )

    assert install_root.is_dir()
    assert all(path.is_dir() for path in install_root.rglob("*"))
    assert not list(skills_dir.rglob("*.tmp"))

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True


def test_install_recovers_process_exit_before_receipt_commit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    _run_install_until_process_exit(
        repo_root=repo_root,
        skills_dir=skills_dir,
        exit_after_destination=install_root / "SKILL.md",
    )

    assert install_state_path.is_file()
    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# vibe\n"
    assert not (install_root / ".vibeskills" / "install-receipt.json").exists()

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )

    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_install_recovers_process_exit_during_staging(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    _run_install_until_staging_exit(repo_root=repo_root, skills_dir=skills_dir)

    state = json.loads(install_state_path.read_text(encoding="utf-8"))
    assert state["status"] == "preparing"
    assert list(install_root.rglob("*.tmp"))
    assert not (install_root / "SKILL.md").exists()

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )

    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_update_recovers_process_exit_before_receipt_commit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )

    _run_install_until_process_exit(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        exit_after_destination=install_root / "SKILL.md",
    )

    assert install_state_path.is_file()
    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"

    update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )

    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_concurrent_install_waits_for_active_transaction(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    marker_path = tmp_path / "apply-started"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    script = textwrap.dedent(
        """
        from pathlib import Path
        import sys
        import time

        import vgo_installer.simple_skill_installer as installer

        repo_root = Path(sys.argv[1])
        skills_dir = Path(sys.argv[2])
        marker_path = Path(sys.argv[3])
        original_apply = installer._apply_install_file_changes

        def slow_apply(changes):
            marker_path.write_text("started\\n", encoding="utf-8")
            time.sleep(1.0)
            original_apply(changes)

        installer._apply_install_file_changes = slow_apply
        installer.install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
        )
        """
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        path
        for path in (
            str(CONTRACTS_SRC),
            str(INSTALLER_SRC),
            environment.get("PYTHONPATH", ""),
        )
        if path
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
            str(repo_root),
            str(skills_dir),
            str(marker_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    deadline = time.monotonic() + 10.0
    while not marker_path.is_file() and process.poll() is None:
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("concurrent install did not reach apply")
        time.sleep(0.02)

    receipt = install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )
    stdout, stderr = process.communicate(timeout=10)

    assert process.returncode == 0, stdout + stderr
    assert receipt["installed_at_utc"] == "2026-07-02T10:00:00Z"
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not (skills_dir / ".vibeskills" / "vibe-install-state.json").exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_uninstall_converges_interrupted_new_install(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    _run_install_until_process_exit(
        repo_root=repo_root,
        skills_dir=skills_dir,
        exit_after_destination=install_root / "SKILL.md",
    )

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is True
    assert result["status"] == "uninstalled"
    assert not install_root.exists()
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_uninstall_recovers_committed_receipt_before_cleanup(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)

    _run_install_until_process_exit(
        repo_root=repo_root,
        skills_dir=skills_dir,
        exit_after_destination=receipt_path,
    )

    assert receipt_path.is_file()
    assert install_state_path.is_file()
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is True
    assert not install_root.exists()
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_committed_install_keeps_journal_when_backup_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    original_unlink = Path.unlink

    def fail_skill_backup_delete(path: Path, *, missing_ok: bool = False) -> None:
        if path.parent == install_root and path.name.startswith(".SKILL.md."):
            raise PermissionError(f"locked backup: {path}")
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", fail_skill_backup_delete)
        with pytest.raises(PermissionError, match="cleanup was incomplete"):
            update_vibe_skill(
                repo_root=next_repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T09:00:00Z",
            )

    assert (install_root / "SKILL.md").read_text(encoding="utf-8") == "# next vibe\n"
    assert install_state_path.is_file()
    assert len(list(install_root.glob(".SKILL.md.*.tmp"))) == 1

    update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )

    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_committed_install_retries_journal_delete_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    original_unlink = Path.unlink

    def fail_install_state_delete(path: Path, *, missing_ok: bool = False) -> None:
        if path == install_state_path:
            raise PermissionError(f"locked state: {path}")
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", fail_install_state_delete)
        with pytest.raises(PermissionError, match="cleanup was incomplete"):
            install_vibe_skill(
                repo_root=repo_root,
                skills_dir=skills_dir,
                installed_at_utc="2026-07-02T09:00:00Z",
            )

    assert (install_root / ".vibeskills" / "install-receipt.json").is_file()
    assert install_state_path.is_file()
    assert not list(install_root.rglob("*.tmp"))

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T10:00:00Z",
    )

    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True
    assert not install_state_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_install_recovery_rejects_journal_temp_path_outside_install_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    install_root = skills_dir / "vibe"
    install_state_path = skills_dir / ".vibeskills" / "vibe-install-state.json"
    outside_file = tmp_path / ".SKILL.md.outside.tmp"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    _write(outside_file, "outside\n")
    _run_install_until_process_exit(
        repo_root=repo_root,
        skills_dir=skills_dir,
        exit_after_destination=install_root / "SKILL.md",
    )
    state = json.loads(install_state_path.read_text(encoding="utf-8"))
    state["changes"][0]["staged_path"] = str(outside_file.resolve())
    _write(install_state_path, json.dumps(state, indent=2) + "\n")

    with pytest.raises(RuntimeError, match="escapes the Vibe install root"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T10:00:00Z",
        )

    assert outside_file.read_text(encoding="utf-8") == "outside\n"
    assert install_state_path.is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows path aliases are Windows-only")
def test_install_rejects_case_alias_package_destinations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _write(repo_root / "config" / "Foo.json", "{}\n")
    _seed_runtime_contract(repo_root)
    monkeypatch.setattr(
        simple_skill_installer,
        "_package_file_relpaths",
        lambda source_root: ["config/Foo.json", "config/foo.json"],
    )

    with pytest.raises(RuntimeError, match="target the same install file"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T08:00:00Z",
        )

    assert not (skills_dir / "vibe" / ".vibeskills" / "install-receipt.json").exists()
    assert not (skills_dir / ".vibeskills" / "vibe-install-state.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows path aliases are Windows-only")
def test_update_accepts_owned_path_case_change(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(repo_root / "config" / "Foo.json", "{\"version\": 1}\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _write(next_repo_root / "config" / "foo.json", "{\"version\": 2}\n")
    _seed_runtime_contract(repo_root, config_files=("config/Foo.json",))
    _seed_runtime_contract(next_repo_root, config_files=("config/foo.json",))
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )

    receipt = update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )

    paths = {entry["path"] for entry in receipt["files"]}
    assert "config/foo.json" in paths
    assert "config/Foo.json" not in paths
    assert (skills_dir / "vibe" / "config" / "foo.json").read_text(encoding="utf-8") == (
        "{\"version\": 2}\n"
    )
    assert check_vibe_skill(skills_dir=skills_dir)["ok"] is True


def test_update_replaces_hardlinks_without_mutating_external_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    next_repo_root = tmp_path / "next-repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# old vibe\n")
    _write(next_repo_root / "SKILL.md", "# next vibe\n")
    _seed_runtime_contract(repo_root)
    _seed_runtime_contract(next_repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    installed_skill = install_root / "SKILL.md"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    external_skill = tmp_path / "external-skill.md"
    external_receipt = tmp_path / "external-receipt.json"
    external_skill.write_bytes(installed_skill.read_bytes())
    external_receipt.write_bytes(receipt_path.read_bytes())
    installed_skill.unlink()
    receipt_path.unlink()
    try:
        os.link(external_skill, installed_skill)
        os.link(external_receipt, receipt_path)
    except OSError as exc:
        pytest.skip(f"hard links are unavailable: {exc}")

    update_vibe_skill(
        repo_root=next_repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )

    assert installed_skill.read_text(encoding="utf-8") == "# next vibe\n"
    assert external_skill.read_text(encoding="utf-8") == "# old vibe\n"
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["installed_at_utc"] == (
        "2026-07-02T09:00:00Z"
    )
    assert json.loads(external_receipt.read_text(encoding="utf-8"))["installed_at_utc"] == (
        "2026-07-02T08:00:00Z"
    )


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


def test_uninstall_preserves_junction_and_external_target_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    external_root = tmp_path / "external"
    external_empty_directory = external_root / "empty"
    external_file = external_root / "data.txt"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    junction = install_root / "user-junction"
    external_empty_directory.mkdir(parents=True)
    _write(external_file, "keep me\n")
    _junction_or_skip(junction, external_root)

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is True
    assert result["status"] == "uninstalled_with_preserved_files"
    assert result["preserved_files"] == ["user-junction"]
    assert junction.is_dir()
    assert external_empty_directory.is_dir()
    assert external_file.read_text(encoding="utf-8") == "keep me\n"

    junction.rmdir()
    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert retry["status"] == "uninstalled"
    assert external_empty_directory.is_dir()
    assert external_file.read_text(encoding="utf-8") == "keep me\n"


def test_uninstall_collects_file_failures_and_keeps_receipt_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    locked_file = install_root / "SKILL.md"
    original_unlink = Path.unlink

    def fail_locked_file(path: Path, *, missing_ok: bool = False) -> None:
        if path == locked_file:
            raise PermissionError(f"locked: {path}")
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", fail_locked_file)
        result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_files"] == ["SKILL.md"]
    assert result["permission_denied_files"] == ["SKILL.md"]
    assert receipt_path.is_file()

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert not install_root.exists()


def test_uninstall_reports_empty_directory_cleanup_failure_before_dropping_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    locked_directory = install_root / "config"
    original_rmdir = Path.rmdir

    def fail_locked_directory(path: Path) -> None:
        if path == locked_directory:
            raise PermissionError(f"locked: {path}")
        original_rmdir(path)

    with monkeypatch.context() as context:
        context.setattr(Path, "rmdir", fail_locked_directory)
        result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_directories"] == ["config"]
    assert result["permission_denied_directories"] == ["config"]
    assert receipt_path.is_file()

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert not install_root.exists()


def test_uninstall_final_root_cleanup_failure_keeps_resumable_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    install_root = skills_dir / "vibe"
    receipt_path = install_root / ".vibeskills" / "install-receipt.json"
    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    original_rmdir = Path.rmdir

    def fail_install_root(path: Path) -> None:
        if path == install_root:
            raise PermissionError(f"locked: {path}")
        original_rmdir(path)

    with monkeypatch.context() as context:
        context.setattr(Path, "rmdir", fail_install_root)
        result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_directories"] == ["."]
    assert result["permission_denied_directories"] == ["."]
    assert not receipt_path.exists()
    assert recovery_path.is_file()

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert not install_root.exists()


def test_uninstall_state_delete_failure_is_retryable_after_root_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    original_unlink = Path.unlink

    def fail_recovery_state_delete(path: Path, *, missing_ok: bool = False) -> None:
        if path == recovery_path:
            raise PermissionError(f"locked: {path}")
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", fail_recovery_state_delete)
        result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["failed_files"] == [".vibeskills/vibe-uninstall-state.json"]
    assert result["permission_denied_files"] == [".vibeskills/vibe-uninstall-state.json"]
    assert not install_root.exists()
    assert recovery_path.is_file()

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert not recovery_path.exists()


def test_uninstall_completion_survives_process_exit_after_state_delete(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    completion_path = skills_dir / ".vibeskills" / "vibe-uninstall-complete.json"

    _run_uninstall_until_state_delete_exit(skills_dir=skills_dir)

    assert not install_root.exists()
    assert not recovery_path.exists()
    assert completion_path.is_file()

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert retry["status"] == "uninstalled"
    assert completion_path.is_file()


def test_uninstall_completion_write_failure_is_visible_and_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    install_root = skills_dir / "vibe"
    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    completion_path = skills_dir / ".vibeskills" / "vibe-uninstall-complete.json"
    original_replace = simple_skill_installer.os.replace

    def fail_completion_write(source: Path, destination: Path) -> None:
        if Path(destination) == completion_path:
            raise PermissionError(f"locked: {destination}")
        original_replace(source, destination)

    with monkeypatch.context() as context:
        context.setattr(simple_skill_installer.os, "replace", fail_completion_write)
        result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is False
    assert result["status"] == "partial_failure"
    assert result["failed_files"] == [".vibeskills/vibe-uninstall-complete.json"]
    assert result["permission_denied_files"] == [
        ".vibeskills/vibe-uninstall-complete.json"
    ]
    assert not install_root.exists()
    assert recovery_path.is_file()
    assert not completion_path.exists()
    assert not list(skills_dir.rglob("*.tmp"))

    retry = uninstall_vibe_skill(skills_dir=skills_dir)

    assert retry["ok"] is True
    assert not recovery_path.exists()
    assert completion_path.is_file()


def test_invalid_reinstall_preserves_uninstall_completion(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    assert uninstall_vibe_skill(skills_dir=skills_dir)["ok"] is True
    completion_path = skills_dir / ".vibeskills" / "vibe-uninstall-complete.json"
    assert completion_path.is_file()

    with pytest.raises(RuntimeError, match="requires release version and asset name"):
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
            source_kind="public_release",
        )

    assert completion_path.is_file()
    retry = uninstall_vibe_skill(skills_dir=skills_dir)
    assert retry["ok"] is True
    assert retry["status"] == "uninstalled"


def test_successful_reinstall_clears_uninstall_completion(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    assert uninstall_vibe_skill(skills_dir=skills_dir)["ok"] is True
    completion_path = skills_dir / ".vibeskills" / "vibe-uninstall-complete.json"
    assert completion_path.is_file()

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
    )

    assert (skills_dir / "vibe" / ".vibeskills" / "install-receipt.json").is_file()
    assert not completion_path.exists()


def test_uninstall_keeps_other_skills_metadata_when_removing_recovery_state(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    skills_dir = tmp_path / "skills"
    _write(repo_root / "SKILL.md", "# vibe\n")
    _seed_runtime_contract(repo_root)
    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T08:00:00Z",
    )
    metadata_file = skills_dir / ".vibeskills" / "other-state.json"
    _write(metadata_file, "{}\n")

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    assert result["ok"] is True
    assert metadata_file.read_text(encoding="utf-8") == "{}\n"
    assert not (metadata_file.parent / "vibe-uninstall-state.json").exists()
    assert not list(skills_dir.rglob("*.tmp"))


def test_reinstall_uses_uninstall_state_without_overwriting_user_files(tmp_path: Path) -> None:
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
    install_root = skills_dir / "vibe"
    user_file = install_root / "notes.md"
    user_file.write_text("keep me\n", encoding="utf-8")

    result = uninstall_vibe_skill(skills_dir=skills_dir)

    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    assert result["ok"] is True
    assert result["status"] == "uninstalled_with_preserved_files"
    assert result["preserved_files"] == ["notes.md"]
    assert recovery_path.is_file()

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
        source_git_commit="def456",
        source_git_dirty=False,
    )

    assert user_file.read_text(encoding="utf-8") == "keep me\n"
    assert (install_root / ".vibeskills" / "install-receipt.json").is_file()
    assert not recovery_path.exists()
    assert check_vibe_skill(skills_dir=skills_dir)["extra_files"] == ["notes.md"]


def test_reinstall_with_receipt_ignores_incomplete_uninstall_state(tmp_path: Path) -> None:
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
    install_root = skills_dir / "vibe"
    recovery_path = skills_dir / ".vibeskills" / "vibe-uninstall-state.json"
    _write(recovery_path, "{\n")

    install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc="2026-07-02T09:00:00Z",
        source_git_commit="def456",
        source_git_dirty=False,
    )

    assert (install_root / ".vibeskills" / "install-receipt.json").is_file()
    assert not recovery_path.exists()


def test_reinstall_from_uninstall_state_rejects_new_package_path_collision(tmp_path: Path) -> None:
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
    install_root = skills_dir / "vibe"
    (install_root / "notes.md").write_text("keep me\n", encoding="utf-8")
    uninstall_vibe_skill(skills_dir=skills_dir)
    user_collision = install_root / "SKILL.md"
    user_collision.write_text("# user-owned\n", encoding="utf-8")

    try:
        install_vibe_skill(
            repo_root=repo_root,
            skills_dir=skills_dir,
            installed_at_utc="2026-07-02T09:00:00Z",
            source_git_commit="def456",
            source_git_dirty=False,
        )
    except RuntimeError as exc:
        assert "Install path exists but is not owned" in str(exc)
    else:
        raise AssertionError("reinstall should reject a new user-owned package path")

    assert user_collision.read_text(encoding="utf-8") == "# user-owned\n"
