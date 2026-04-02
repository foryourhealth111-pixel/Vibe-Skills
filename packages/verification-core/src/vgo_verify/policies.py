from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


@dataclass(slots=True)
class GovernanceContext:
    repo_root: Path
    governance_path: Path
    governance: dict[str, Any]
    canonical_root: Path
    packaging: dict[str, Any]
    runtime_config: dict[str, Any]
    mirror_targets: list[dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_posix(path: Path | str) -> str:
    return Path(path).as_posix()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def remove_ignored_keys(node: Any, ignore_keys: set[str]) -> Any:
    if isinstance(node, dict):
        return {
            key: remove_ignored_keys(value, ignore_keys)
            for key, value in sorted(node.items())
            if key not in ignore_keys
        }
    if isinstance(node, list):
        return [remove_ignored_keys(item, ignore_keys) for item in node]
    return node


def normalized_json_hash(path: Path, ignore_keys: set[str]) -> str:
    normalized = remove_ignored_keys(load_json(path), ignore_keys)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_parity(reference: Path, candidate: Path, ignore_json_keys: set[str]) -> bool:
    if not reference.exists() or not candidate.exists():
        return False
    if reference.suffix.lower() == ".json" and candidate.suffix.lower() == ".json":
        return normalized_json_hash(reference, ignore_json_keys) == normalized_json_hash(candidate, ignore_json_keys)
    return file_hash(reference) == file_hash(candidate)


def is_ignored_runtime_artifact(path: str | Path) -> bool:
    candidate = Path(path)
    if any(part in RUNTIME_IGNORED_DIR_NAMES for part in candidate.parts):
        return True
    if candidate.name in RUNTIME_IGNORED_FILE_NAMES:
        return True
    if any(candidate.name.startswith(prefix) for prefix in RUNTIME_IGNORED_FILE_PREFIXES):
        return True
    if candidate.suffix in RUNTIME_IGNORED_SUFFIXES:
        return True
    return False


def relative_file_list(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        to_posix(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and not is_ignored_runtime_artifact(path.relative_to(root))
    )


def resolve_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    candidates: list[Path] = []
    while True:
        if (current / "config" / "version-governance.json").exists():
            candidates.append(current)
        if current.parent == current:
            break
        current = current.parent
    if not candidates:
        raise RuntimeError(f"Unable to resolve VCO repo root from: {start_path}")
    git_candidates = [candidate for candidate in candidates if (candidate / ".git").exists()]
    if git_candidates:
        return git_candidates[-1]
    return candidates[-1]


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
        payload = load_json(manifest_path)
        files.extend(str(item) for item in (payload.get("files") or []))
        directories.extend(str(item) for item in (payload.get("directories") or []))
    allow_installed_only = list(packaging.get("allow_installed_only") or packaging.get("allow_bundled_only") or [])
    return {
        "runtime_payload": {
            "files": _dedupe_ordered(files),
            "directories": _dedupe_ordered(directories),
        },
        "mirror": {
            "files": _dedupe_ordered(files),
            "directories": _dedupe_ordered(directories),
        },
        "manifests": manifests,
        "target_overrides": packaging.get("target_overrides") or {},
        "allow_installed_only": allow_installed_only,
        "allow_bundled_only": allow_installed_only,
        "normalized_json_ignore_keys": list(packaging.get("normalized_json_ignore_keys") or DEFAULT_IGNORE_JSON_KEYS),
    }


def mirror_topology_targets(governance: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    topology = governance.get("mirror_topology") or {}
    targets = topology.get("targets") or []
    if not targets:
        source = governance.get("source_of_truth") or {}
        targets = [
            {
                "id": "canonical",
                "path": source.get("canonical_root") or ".",
                "role": "canonical",
            },
        ]
        bundled_root = source.get("bundled_root")
        if bundled_root:
            targets.append({"id": "bundled", "path": bundled_root, "role": "mirror"})
        nested_root = source.get("nested_bundled_root")
        if nested_root:
            targets.append({"id": "nested_bundled", "path": nested_root, "role": "mirror"})

    normalized: list[dict[str, Any]] = []
    for target in targets:
        rel = str(target.get("path") or "").strip()
        if not rel:
            continue
        full_path = (repo_root / rel).resolve()
        role = str(target.get("role") or "mirror")
        normalized.append(
            {
                "id": str(target.get("id") or ""),
                "path": rel.replace("\\", "/"),
                "full_path": full_path,
                "role": role,
                "is_canonical": role == "canonical",
            }
        )
    return normalized


def merge_runtime_config(governance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}
    merged = dict(defaults)
    for key, value in runtime.items():
        if value is None:
            continue
        merged[key] = value
    if "required_runtime_markers" in defaults:
        merged["required_runtime_markers"] = list(runtime.get("required_runtime_markers") or defaults["required_runtime_markers"])
    return merged


def installed_runtime_materialized(repo_root: Path, runtime_cfg: dict[str, Any]) -> bool:
    required_markers = list(runtime_cfg.get("required_runtime_markers") or [])
    if not required_markers:
        return False
    return all((repo_root / marker).exists() for marker in required_markers)


def enforce_execution_context(context: GovernanceContext, script_path: Path) -> None:
    policy = context.governance.get("execution_context_policy") or {}
    require_outer_git_root = bool(policy.get("require_outer_git_root", True))
    fail_if_under_mirror = bool(policy.get("fail_if_script_path_is_under_mirror_root", True))
    if (
        require_outer_git_root
        and not (context.repo_root / ".git").exists()
        and not installed_runtime_materialized(context.repo_root, context.runtime_config)
    ):
        raise RuntimeError(
            f"Execution-context lock failed: resolved repo root is not the outer git root -> {context.repo_root}"
        )
    if not fail_if_under_mirror:
        return
    resolved_script = script_path.resolve()
    for target in context.mirror_targets:
        if target["is_canonical"]:
            continue
        try:
            resolved_script.relative_to(target["full_path"])
        except ValueError:
            continue
        raise RuntimeError(
            "Execution-context lock failed: governance/verify scripts must run from the canonical repo tree, "
            f"not from mirror targets. target={target['id']} script={resolved_script} repoRoot={context.repo_root}"
        )


def load_governance_context(
    script_path: Path,
    runtime_defaults: dict[str, Any],
    enforce_context: bool = True,
) -> GovernanceContext:
    repo_root = resolve_repo_root(script_path)
    governance_path = repo_root / "config" / "version-governance.json"
    if not governance_path.exists():
        raise RuntimeError(f"version-governance config not found: {governance_path}")
    governance = load_json(governance_path)
    targets = mirror_topology_targets(governance, repo_root)
    canonical_target_id = (governance.get("mirror_topology") or {}).get("canonical_target_id") or "canonical"
    canonical = next((target for target in targets if target["id"] == canonical_target_id), None)
    if canonical is None:
        canonical = next((target for target in targets if target["is_canonical"]), None)
    if canonical is None:
        raise RuntimeError("mirror topology does not define a canonical target.")
    context = GovernanceContext(
        repo_root=repo_root,
        governance_path=governance_path,
        governance=governance,
        canonical_root=Path(canonical["full_path"]),
        packaging=resolve_packaging_contract(governance, repo_root),
        runtime_config=merge_runtime_config(governance, runtime_defaults),
        mirror_targets=targets,
    )
    if enforce_context:
        enforce_execution_context(context, script_path)
    return context
