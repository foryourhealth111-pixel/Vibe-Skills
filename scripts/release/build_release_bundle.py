from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_SRC = REPO_ROOT / "packages" / "installer-core" / "src"
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.simple_skill_installer import runtime_surface_relpaths

PUBLIC_RELEASE_ROOT_FILES = (
    "README.md",
    "README.zh.md",
    "SKILL.md",
    "install.ps1",
    "install.sh",
    "update.ps1",
    "update.sh",
    "check.ps1",
    "check.sh",
    "uninstall.ps1",
    "uninstall.sh",
)
PUBLIC_RELEASE_DIRS = (
    "references",
    "docs",
    "mcp",
    "templates",
    "adapters",
    "packages/installer-core",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _iter_release_relpaths(source_root: Path) -> list[str]:
    relpaths: set[str] = set(runtime_surface_relpaths(source_root))
    for relpath in (*PUBLIC_RELEASE_ROOT_FILES, *PUBLIC_RELEASE_DIRS):
        source = source_root / relpath
        if not source.exists():
            continue
        if source.is_file():
            relpaths.add(relpath)
            continue
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            if "__pycache__" in file_path.parts or file_path.suffix == ".pyc":
                continue
            relpaths.add(file_path.relative_to(source_root).as_posix())
    return sorted(relpaths)


def _copy_release_tree(source_root: Path, asset_root: Path, relpaths: list[str]) -> None:
    if asset_root.exists():
        shutil.rmtree(asset_root)
    asset_root.mkdir(parents=True, exist_ok=True)
    for relpath in relpaths:
        _copy_file(source_root / relpath, asset_root / relpath)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_entries(asset_root: Path, relpaths: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for relpath in relpaths:
        file_path = asset_root / relpath
        if file_path.is_file():
            entries.append({"path": relpath, "sha256": _sha256_file(file_path)})
    return entries


def _payload_digest(entries: list[dict[str, str]]) -> str:
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _zip_asset_root(asset_root: Path, asset_zip_path: Path) -> None:
    if asset_zip_path.exists():
        asset_zip_path.unlink()
    with zipfile.ZipFile(asset_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for file_path in sorted(path for path in asset_root.rglob("*") if path.is_file()):
            archive_name = Path(asset_root.name) / file_path.relative_to(asset_root)
            handle.write(file_path, archive_name.as_posix())


def build_release_bundle(distribution_manifest_path: Path | str, output_dir: Path | str) -> dict[str, Any]:
    manifest_path = Path(distribution_manifest_path).resolve()
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    distribution_manifest = load_json(manifest_path)
    governance = load_json((REPO_ROOT / "config" / "version-governance.json").resolve())
    release = dict(governance.get("release") or {})
    release_version = str(release.get("version") or "").strip()
    asset_dir_name = f"vibe-skills-{release_version}-public"
    asset_file_name = f"{asset_dir_name}.zip"
    asset_root = output_root / asset_dir_name
    asset_zip_path = output_root / asset_file_name

    relpaths = _iter_release_relpaths(REPO_ROOT)
    _copy_release_tree(REPO_ROOT, asset_root, relpaths)
    payload_entries = _payload_entries(asset_root, relpaths)
    payload_digest_sha256 = _payload_digest(payload_entries)

    bundle = {
        "schema_version": 1,
        "generated": True,
        "host_id": str(distribution_manifest.get("host_id") or ""),
        "profile": str(distribution_manifest.get("profile") or ""),
        "distribution_manifest": str(manifest_path),
        "release": {
            "version": release_version,
            "channel": str(release.get("channel") or ""),
            "updated": str(release.get("updated") or ""),
        },
        "public_install": {
            "source_kind": "public_release",
            "host_neutral": True,
            "skills_dir_centered": True,
        },
        "asset": {
            "root_dir_name": asset_dir_name,
            "file_name": asset_file_name,
            "payload_digest_sha256": payload_digest_sha256,
        },
        "inputs": dict(distribution_manifest.get("inputs") or {}),
        "runtime_payload_roles": dict(distribution_manifest.get("runtime_payload_roles") or {}),
        "runtime_config_payload_roles": dict(distribution_manifest.get("runtime_config_payload_roles") or {}),
        "runtime_core_payload_roles": dict(distribution_manifest.get("runtime_core_payload_roles") or {}),
        "governance_runtime_roles": dict(distribution_manifest.get("governance_runtime_roles") or {}),
        "ownership": {
            "semantic_owner": "scripts/release/build_release_bundle.py",
            "generated_outputs_only": True,
        },
    }
    write_json(output_root / "release-bundle.json", bundle)
    write_json(asset_root / "release-bundle.json", bundle)
    _zip_asset_root(asset_root, asset_zip_path)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a release bundle from a generated distribution manifest.")
    parser.add_argument("--distribution-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    bundle = build_release_bundle(args.distribution_manifest, args.output_dir)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
