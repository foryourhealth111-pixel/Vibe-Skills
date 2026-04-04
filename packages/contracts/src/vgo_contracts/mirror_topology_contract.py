from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_CANONICAL_TARGET_ID = "canonical"
DEFAULT_BUNDLED_ROOT = "bundled/skills/vibe"
DEFAULT_NESTED_MATERIALIZATION_MODE = "release_install_only"


def _normalize_relpath(value: str | None, *, default: str | None = None) -> str | None:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return default
    normalized = Path(text).as_posix().strip()
    if normalized in {"", "/"}:
        return default
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or default


def resolve_mirror_topology_targets(governance: dict[str, Any]) -> list[dict[str, Any]]:
    topology = governance.get("mirror_topology") or {}
    targets = list(topology.get("targets") or [])
    if not targets:
        source = governance.get("source_of_truth") or {}
        targets = [
            {
                "id": DEFAULT_CANONICAL_TARGET_ID,
                "path": source.get("canonical_root") or ".",
                "role": "canonical",
            }
        ]
        bundled_root = _normalize_relpath(source.get("bundled_root"))
        if bundled_root:
            targets.append({"id": "bundled", "path": bundled_root, "role": "mirror"})
        nested_root = _normalize_relpath(source.get("nested_bundled_root"))
        if nested_root:
            targets.append({"id": "nested_bundled", "path": nested_root, "role": "mirror"})

    normalized: list[dict[str, Any]] = []
    for target in targets:
        target_id = str(target.get("id") or "").strip()
        target_path = _normalize_relpath(target.get("path"), default=".")
        if not target_id or not target_path:
            continue
        normalized_target = dict(target)
        normalized_target["id"] = target_id
        normalized_target["path"] = target_path
        normalized_target["role"] = str(
            target.get("role") or ("canonical" if target_id == DEFAULT_CANONICAL_TARGET_ID else "mirror")
        ).strip() or "mirror"
        normalized.append(normalized_target)
    return normalized


def resolve_canonical_mirror_relpath(governance: dict[str, Any]) -> str:
    topology = governance.get("mirror_topology") or {}
    canonical_target_id = (
        str(topology.get("canonical_target_id") or DEFAULT_CANONICAL_TARGET_ID).strip()
        or DEFAULT_CANONICAL_TARGET_ID
    )
    targets = resolve_mirror_topology_targets(governance)
    for target in targets:
        if str(target.get("id") or "") == canonical_target_id:
            return str(target["path"])
    for target in targets:
        if str(target.get("role") or "") == "canonical":
            return str(target["path"])
    return "."


def resolve_generated_nested_compatibility_suffix(governance: dict[str, Any]) -> Path | None:
    packaging = governance.get("packaging") or {}
    generated = packaging.get("generated_compatibility") or {}
    nested_runtime = generated.get("nested_runtime_root") or {}
    relative_path = _normalize_relpath(nested_runtime.get("relative_path"))
    materialization_mode = str(nested_runtime.get("materialization_mode") or "").strip()
    if relative_path:
        if not materialization_mode:
            materialization_mode = "install_only"
        if materialization_mode not in {"install_only", DEFAULT_NESTED_MATERIALIZATION_MODE}:
            return None
        return Path(*relative_path.split("/"))

    topology_targets = resolve_mirror_topology_targets(governance)
    bundled_path = None
    nested_path = None
    nested_materialization_mode = None

    for target in topology_targets:
        target_id = str(target.get("id") or "").strip().lower()
        if target_id == "bundled":
            bundled_path = _normalize_relpath(target.get("path"))
        elif target_id == "nested_bundled":
            nested_path = _normalize_relpath(target.get("path"))
            nested_materialization_mode = str(target.get("materialization_mode") or "").strip()

    source = governance.get("source_of_truth") or {}
    if not bundled_path:
        bundled_path = _normalize_relpath(source.get("bundled_root"), default=DEFAULT_BUNDLED_ROOT)
    if not nested_path:
        nested_path = _normalize_relpath(source.get("nested_bundled_root"))
    if not nested_path:
        nested_path = f"{bundled_path}/{bundled_path}"
    if not nested_materialization_mode:
        nested_materialization_mode = DEFAULT_NESTED_MATERIALIZATION_MODE
    if nested_materialization_mode != DEFAULT_NESTED_MATERIALIZATION_MODE:
        return None

    bundled_norm = str(bundled_path).replace("\\", "/").strip("/")
    nested_norm = str(nested_path).replace("\\", "/").strip("/")
    prefix = f"{bundled_norm}/"
    if not nested_norm.startswith(prefix):
        return None

    suffix = nested_norm[len(prefix):].strip("/")
    if not suffix:
        return None
    return Path(*suffix.split("/"))
