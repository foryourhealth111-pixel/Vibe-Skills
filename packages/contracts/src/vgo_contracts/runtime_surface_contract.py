from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
