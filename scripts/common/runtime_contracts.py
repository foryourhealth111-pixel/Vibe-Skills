#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

try:
    from vgo_contracts.installed_runtime_contract import (
        COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT,
        DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE,
        DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE,
        DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE,
        DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE,
        DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION,
        DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH,
        DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT,
        DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR,
        DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH,
        FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT,
        default_coherence_runtime_config,
        default_freshness_runtime_config,
        default_installed_runtime_config,
        merge_installed_runtime_config,
    )
    from vgo_contracts.runtime_surface_contract import (
        DEFAULT_IGNORE_JSON_KEYS,
        DEFAULT_PACKAGING_DIRECTORIES,
        DEFAULT_PACKAGING_FILES,
        RUNTIME_IGNORED_DIR_NAMES,
        RUNTIME_IGNORED_FILE_NAMES,
        RUNTIME_IGNORED_FILE_PREFIXES,
        RUNTIME_IGNORED_SUFFIXES,
        SKILL_ONLY_ACTIVATION_HOSTS,
        is_ignored_runtime_artifact,
        load_json_file,
        resolve_packaging_contract,
        uses_skill_only_activation,
    )
except ModuleNotFoundError:
    DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH = "skills/vibe"
    DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH = "skills/vibe/outputs/runtime-freshness-receipt.json"
    DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE = "scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
    DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE = "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
    DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE = "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE = "scripts/verify/runtime_neutral/freshness_gate.py"
    DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT = "scripts/runtime/invoke-vibe-runtime.ps1"
    DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION = 1
    DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR = "warn_and_skip_authoritative_runtime_gate"

    FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT = (
        "SKILL.md",
        "config/version-governance.json",
        "scripts/router/resolve-pack-route.ps1",
        "scripts/common/vibe-governance-helpers.ps1",
    )

    COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT = (
        "SKILL.md",
        "config/version-governance.json",
        "install.ps1",
        "check.ps1",
        "scripts/common/vibe-governance-helpers.ps1",
        "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
        "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
        "scripts/runtime/invoke-vibe-runtime.ps1",
        "scripts/router/resolve-pack-route.ps1",
    )

    def default_installed_runtime_config() -> dict[str, Any]:
        return {
            "target_relpath": DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH,
            "receipt_relpath": DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH,
            "post_install_gate": DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE,
            "coherence_gate": DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE,
            "frontmatter_gate": DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE,
            "neutral_freshness_gate": DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE,
            "runtime_entrypoint": DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT,
            "receipt_contract_version": DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION,
            "shell_degraded_behavior": DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR,
            "required_runtime_markers": list(COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT),
            "require_nested_bundled_root": False,
        }

    def default_freshness_runtime_config() -> dict[str, Any]:
        defaults = default_installed_runtime_config()
        defaults["required_runtime_markers"] = list(FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT)
        return defaults

    def default_coherence_runtime_config() -> dict[str, Any]:
        return default_installed_runtime_config()

    def merge_installed_runtime_config(governance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}
        merged = dict(defaults)
        for key, value in runtime.items():
            if value is None:
                continue
            merged[key] = value
        if "required_runtime_markers" in defaults:
            merged["required_runtime_markers"] = list(runtime.get("required_runtime_markers") or defaults["required_runtime_markers"])
        return merged

    SKILL_ONLY_ACTIVATION_HOSTS = frozenset(
        {
            "claude-code",
            "cursor",
            "windsurf",
            "openclaw",
            "opencode",
        }
    )

    RUNTIME_IGNORED_DIR_NAMES = frozenset(
        {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            "venv",
        }
    )
    RUNTIME_IGNORED_SUFFIXES = frozenset({".pyc"})
    RUNTIME_IGNORED_FILE_NAMES = frozenset({".coverage"})
    RUNTIME_IGNORED_FILE_PREFIXES = (".coverage.",)

    DEFAULT_PACKAGING_FILES = (
        "SKILL.md",
        "check.ps1",
        "check.sh",
        "install.ps1",
        "install.sh",
    )
    DEFAULT_PACKAGING_DIRECTORIES = (
        "config",
        "protocols",
        "references",
        "docs",
        "scripts",
    )
    DEFAULT_IGNORE_JSON_KEYS = ("updated", "generated_at")

    def uses_skill_only_activation(host_id: str | None) -> bool:
        return (host_id or "").strip().lower() in SKILL_ONLY_ACTIVATION_HOSTS

    def is_ignored_runtime_artifact(path: str | Path) -> bool:
        candidate = Path(path)
        if any(part in RUNTIME_IGNORED_DIR_NAMES for part in candidate.parts):
            return True

        name = candidate.name
        if name in RUNTIME_IGNORED_FILE_NAMES:
            return True
        if any(name.startswith(prefix) for prefix in RUNTIME_IGNORED_FILE_PREFIXES):
            return True
        if candidate.suffix in RUNTIME_IGNORED_SUFFIXES:
            return True

        return False

    def load_json_file(path: Path) -> Any:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)

    def _dedupe_ordered(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            candidate = str(value or "").replace("\\", "/").strip("/")
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            result.append(candidate)
        return result

    def _iter_packaging_manifests(raw_manifests: Any) -> list[dict[str, str]]:
        manifests: list[dict[str, str]] = []
        if isinstance(raw_manifests, list):
            for item in raw_manifests:
                if not isinstance(item, dict):
                    continue
                manifest_id = str(item.get("id") or "").strip()
                manifest_path = str(item.get("path") or "").strip()
                if manifest_path:
                    manifests.append({"id": manifest_id, "path": manifest_path.replace("\\", "/")})
            return manifests

        if isinstance(raw_manifests, dict):
            for key, value in raw_manifests.items():
                if isinstance(value, dict):
                    manifest_path = str(value.get("path") or "").strip()
                else:
                    manifest_path = str(value or "").strip()
                if manifest_path:
                    manifests.append({"id": str(key).strip(), "path": manifest_path.replace("\\", "/")})
        return manifests

    def resolve_packaging_contract(governance: dict[str, Any], repo_root: Path) -> dict[str, Any]:
        packaging = governance.get("packaging") or {}
        runtime_payload = packaging.get("runtime_payload") or packaging.get("mirror") or {}
        files = list(runtime_payload.get("files") or DEFAULT_PACKAGING_FILES)
        directories = list(runtime_payload.get("directories") or DEFAULT_PACKAGING_DIRECTORIES)
        manifests = _iter_packaging_manifests(packaging.get("manifests") or [])

        for manifest in manifests:
            manifest_path = repo_root / manifest["path"]
            if not manifest_path.exists():
                raise RuntimeError(f"packaging manifest not found: {manifest_path}")
            payload = load_json_file(manifest_path)
            files.extend(str(item) for item in (payload.get("files") or []))
            directories.extend(str(item) for item in (payload.get("directories") or []))

        allow_installed_only = list(packaging.get("allow_installed_only") or packaging.get("allow_bundled_only") or [])
        resolved_files = _dedupe_ordered(files)
        resolved_directories = _dedupe_ordered(directories)
        return {
            "runtime_payload": {
                "files": resolved_files,
                "directories": resolved_directories,
            },
            "mirror": {
                "files": resolved_files,
                "directories": resolved_directories,
            },
            "manifests": manifests,
            "target_overrides": packaging.get("target_overrides") or {},
            "allow_installed_only": allow_installed_only,
            "allow_bundled_only": allow_installed_only,
            "normalized_json_ignore_keys": list(packaging.get("normalized_json_ignore_keys") or DEFAULT_IGNORE_JSON_KEYS),
        }

__all__ = [
    "COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT",
    "DEFAULT_IGNORE_JSON_KEYS",
    "DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE",
    "DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE",
    "DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE",
    "DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE",
    "DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION",
    "DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH",
    "DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT",
    "DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR",
    "DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH",
    "DEFAULT_PACKAGING_DIRECTORIES",
    "DEFAULT_PACKAGING_FILES",
    "FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT",
    "RUNTIME_IGNORED_DIR_NAMES",
    "RUNTIME_IGNORED_FILE_NAMES",
    "RUNTIME_IGNORED_FILE_PREFIXES",
    "RUNTIME_IGNORED_SUFFIXES",
    "SKILL_ONLY_ACTIVATION_HOSTS",
    "default_coherence_runtime_config",
    "default_freshness_runtime_config",
    "default_installed_runtime_config",
    "is_ignored_runtime_artifact",
    "load_json_file",
    "merge_installed_runtime_config",
    "resolve_packaging_contract",
    "uses_skill_only_activation",
]


def _emit_installed_runtime_config(mode: str) -> int:
    loaders = {
        "installed": default_installed_runtime_config,
        "freshness": default_freshness_runtime_config,
        "coherence": default_coherence_runtime_config,
    }
    payload = loaders[mode]()
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runtime contract bridge helpers")
    subparsers = parser.add_subparsers(dest="command")

    config_parser = subparsers.add_parser(
        "installed-runtime-config",
        help="Emit installed-runtime contract defaults as JSON for wrapper consumers.",
    )
    config_parser.add_argument(
        "--mode",
        choices=("installed", "freshness", "coherence"),
        default="installed",
    )

    args = parser.parse_args(argv)
    if args.command == "installed-runtime-config":
        return _emit_installed_runtime_config(args.mode)
    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
