from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.runtime_surface_contract import load_json_file, resolve_packaging_contract


RUNTIME_SURFACE_PREFIXES = (
    "SKILL.md",
    "core/skill-contracts/",
    "config/",
    "protocols/",
    "apps/vgo-cli/",
    "packages/contracts/",
    "packages/runtime-core/",
    "packages/verification-core/",
    "scripts/common/",
    "scripts/runtime/",
    "scripts/router/",
    "scripts/verify/",
)
PACKAGE_EXCLUDED_FILES = {
    "apps/vgo-cli/src/vgo_cli/install_gates.py",
    "apps/vgo-cli/src/vgo_cli/install_support.py",
    "apps/vgo-cli/src/vgo_cli/installer_bridge.py",
    "apps/vgo-cli/src/vgo_cli/upgrade_service.py",
    "packages/verification-core/src/vgo_verify/bio_science_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py",
}
PACKAGE_RUNTIME_TEST_ENTRYPOINTS = {
    "packages/verification-core/src/vgo_verify/test_baseline_audit.py",
}
RECEIPT_RELPATH = ".vibeskills/install-receipt.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return payload


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _matches_surface_prefix(relpath: str) -> bool:
    if relpath == "SKILL.md":
        return True
    return any(relpath.startswith(prefix) for prefix in RUNTIME_SURFACE_PREFIXES if prefix != "SKILL.md")


def _is_package_development_test(relpath: str) -> bool:
    if relpath in PACKAGE_RUNTIME_TEST_ENTRYPOINTS:
        return False
    if not relpath.startswith(("packages/runtime-core/", "packages/verification-core/")):
        return False
    return Path(relpath).name.startswith("test_") and relpath.endswith(".py")


def _should_copy_runtime_surface_file(relpath: str) -> bool:
    normalized = Path(relpath).as_posix()
    if "__pycache__" in Path(normalized).parts or normalized.endswith(".pyc"):
        return False
    if normalized in PACKAGE_EXCLUDED_FILES:
        return False
    if _is_package_development_test(normalized):
        return False
    return _matches_surface_prefix(normalized)


def _copy_tree(source_root: Path, install_root: Path, relpath: str) -> None:
    source = source_root / relpath
    if not source.exists():
        return
    if source.is_file():
        _copy_file(source, install_root / relpath)
        return
    for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
        installed_relpath = file_path.relative_to(source_root).as_posix()
        if "__pycache__" in file_path.parts or file_path.suffix == ".pyc":
            continue
        if installed_relpath in PACKAGE_EXCLUDED_FILES:
            continue
        if _is_package_development_test(installed_relpath):
            continue
        _copy_file(file_path, install_root / installed_relpath)


def runtime_surface_relpaths(source_root: Path) -> list[str]:
    governance_path = source_root / "config" / "version-governance.json"
    if not governance_path.is_file():
        raise RuntimeError(f"Missing runtime governance contract: {governance_path}")

    packaging = resolve_packaging_contract(load_json_file(governance_path), source_root)
    relpaths: set[str] = set()
    for relpath in packaging["mirror"]["files"]:
        normalized = Path(relpath).as_posix()
        source = source_root / normalized
        if source.is_file() and _should_copy_runtime_surface_file(normalized):
            relpaths.add(normalized)

    for relpath in packaging["mirror"]["directories"]:
        source = source_root / relpath
        if not source.exists():
            continue
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            installed_relpath = file_path.relative_to(source_root).as_posix()
            if _should_copy_runtime_surface_file(installed_relpath):
                relpaths.add(installed_relpath)

    return sorted(relpaths)


def _package_file_relpaths(source_root: Path) -> list[str]:
    relpaths: list[str] = []
    for relpath in runtime_surface_relpaths(source_root):
        source = source_root / relpath
        if not source.exists():
            continue
        relpaths.append(relpath)
    return sorted(set(relpaths))


def _copy_package_files(source_root: Path, install_root: Path, relpaths: list[str]) -> None:
    for relpath in relpaths:
        _copy_file(source_root / relpath, install_root / relpath)


def _installed_files(install_root: Path, relpaths: list[str]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for relpath in relpaths:
        file_path = install_root / relpath
        if not file_path.is_file():
            continue
        files.append({"path": relpath, "sha256": _sha256_file(file_path)})
    return files


def _receipt_file_paths(receipt: dict[str, object]) -> set[str]:
    owned: set[str] = set()
    for entry in receipt.get("files") or []:
        if isinstance(entry, dict):
            owned.add(str(entry["path"]))
    return owned


def _remove_retired_owned_files(install_root: Path, *, old_owned: set[str], next_owned: set[str]) -> None:
    for relpath in sorted(old_owned - next_owned, reverse=True):
        file_path = install_root / relpath
        if file_path.is_file():
            file_path.unlink()


def _receipt_path(skills_dir: Path) -> Path:
    return skills_dir.resolve() / "vibe" / RECEIPT_RELPATH


def _scoped_check_result(payload: dict[str, object]) -> dict[str, object]:
    ok = bool(payload.get("ok"))
    return {
        **payload,
        "scope": "installed_vibe_skill",
        "result": "passed" if ok else "failed",
        "proves": [
            "Vibe install receipt exists",
            "receipt-owned files are present",
            "receipt-owned file hashes match",
        ],
        "does_not_prove": [
            "task completion",
            "material skill execution",
            "runtime coherent",
            "delivery accepted",
        ],
    }


def install_vibe_skill(
    *,
    repo_root: Path,
    skills_dir: Path,
    installed_at_utc: str,
    source_kind: str = "developer_repo",
    source_git_commit: str = "",
    source_git_dirty: bool = False,
    release_version: str = "",
    release_asset_name: str = "",
    release_asset_digest: str = "",
    installer_version: str = "0.1.0",
    package_version: str = "0.1.0",
) -> dict[str, object]:
    source_root = repo_root.resolve()
    resolved_skills_dir = skills_dir.resolve()
    install_root = resolved_skills_dir / "vibe"
    receipt_path = install_root / RECEIPT_RELPATH
    if install_root.exists() and not receipt_path.is_file():
        raise RuntimeError(f"Install root already exists without a Vibe install receipt: {install_root}")

    install_root.mkdir(parents=True, exist_ok=True)
    next_owned = _package_file_relpaths(source_root)
    old_owned: set[str] = set()
    if receipt_path.is_file():
        old_owned = _receipt_file_paths(_read_json(receipt_path))
    for relpath in next_owned:
        destination = install_root / relpath
        if destination.exists() and relpath not in old_owned:
            raise RuntimeError(f"Install path exists but is not owned by the Vibe receipt: {destination}")
    _remove_retired_owned_files(install_root, old_owned=old_owned, next_owned=set(next_owned))

    _copy_package_files(source_root, install_root, next_owned)

    files = _installed_files(install_root, next_owned)
    package_digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    receipt: dict[str, object] = {
        "schema_version": 1,
        "receipt_kind": "vibe-skill-install",
        "skill_id": "vibe",
        "source_kind": str(source_kind or "").strip() or "developer_repo",
        "skills_dir": str(resolved_skills_dir),
        "install_root": str(install_root.resolve()),
        "installed_at_utc": installed_at_utc,
        "installer_version": installer_version,
        "package_version": package_version,
        "package_digest_sha256": package_digest,
        "files": files,
    }
    if receipt["source_kind"] == "public_release":
        version = str(release_version or "").strip()
        asset_name = str(release_asset_name or "").strip()
        if not version or not asset_name:
            raise RuntimeError("Public release install requires release version and asset name.")
        release_payload: dict[str, object] = {
            "version": version,
            "asset_name": asset_name,
        }
        digest = str(release_asset_digest or "").strip()
        if digest:
            release_payload["asset_digest_sha256"] = digest
        receipt["release"] = release_payload
    else:
        receipt["source_path"] = str(source_root)
        receipt["source_git_commit"] = source_git_commit
        receipt["source_git_dirty"] = bool(source_git_dirty)
    _write_json(receipt_path, receipt)
    return receipt


def check_vibe_skill(*, skills_dir: Path) -> dict[str, object]:
    receipt_path = _receipt_path(skills_dir)
    if not receipt_path.is_file():
        return _scoped_check_result({"ok": False, "missing_receipt": str(receipt_path)})

    receipt = _read_json(receipt_path)
    install_root = Path(str(receipt["install_root"]))
    missing_files: list[str] = []
    drifted_files: list[str] = []
    receipt_files: set[str] = set()
    for entry in receipt.get("files") or []:
        if not isinstance(entry, dict):
            continue
        relpath = str(entry["path"])
        receipt_files.add(relpath)
        expected_sha = str(entry["sha256"])
        file_path = install_root / relpath
        if not file_path.is_file():
            missing_files.append(relpath)
            continue
        if _sha256_file(file_path) != expected_sha:
            drifted_files.append(relpath)

    actual_files = {
        path.relative_to(install_root).as_posix()
        for path in install_root.rglob("*")
        if path.is_file() and path.relative_to(install_root).as_posix() != RECEIPT_RELPATH
    }
    extra_files = sorted(actual_files - receipt_files)

    return _scoped_check_result({
        "ok": not missing_files and not drifted_files,
        "missing_files": missing_files,
        "drifted_files": drifted_files,
        "extra_files": extra_files,
    })


def update_vibe_skill(
    *,
    repo_root: Path,
    skills_dir: Path,
    installed_at_utc: str,
    source_kind: str = "developer_repo",
    source_git_commit: str = "",
    source_git_dirty: bool = False,
    release_version: str = "",
    release_asset_name: str = "",
    release_asset_digest: str = "",
    installer_version: str = "0.1.0",
    package_version: str = "0.1.0",
    ) -> dict[str, object]:
    check_result = check_vibe_skill(skills_dir=skills_dir)
    if not check_result.get("ok"):
        raise RuntimeError(f"Refusing to update drifted Vibe install: {check_result}")
    return install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc=installed_at_utc,
        source_kind=source_kind,
        source_git_commit=source_git_commit,
        source_git_dirty=source_git_dirty,
        release_version=release_version,
        release_asset_name=release_asset_name,
        release_asset_digest=release_asset_digest,
        installer_version=installer_version,
        package_version=package_version,
    )


def uninstall_vibe_skill(*, skills_dir: Path) -> dict[str, object]:
    receipt_path = _receipt_path(skills_dir)
    if not receipt_path.is_file():
        raise RuntimeError(f"Vibe install receipt is missing: {receipt_path}")

    receipt = _read_json(receipt_path)
    install_root = Path(str(receipt["install_root"]))
    removed_files: list[str] = []
    for entry in receipt.get("files") or []:
        if not isinstance(entry, dict):
            continue
        relpath = str(entry["path"])
        file_path = install_root / relpath
        if file_path.is_file():
            file_path.unlink()
            removed_files.append(relpath)

    receipt_path.unlink()
    for directory in sorted((path for path in install_root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        install_root.rmdir()
    except OSError:
        pass

    return {"removed_files": sorted(removed_files)}


__all__ = [
    "check_vibe_skill",
    "install_vibe_skill",
    "runtime_surface_relpaths",
    "uninstall_vibe_skill",
    "update_vibe_skill",
]
