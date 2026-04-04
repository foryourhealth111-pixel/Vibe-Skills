from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._bootstrap import ensure_contracts_src_on_path
from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root

ensure_contracts_src_on_path()

from vgo_contracts.installed_runtime_contract import (
    default_coherence_runtime_config,
    default_freshness_runtime_config,
    merge_installed_runtime_config,
)
from vgo_contracts.runtime_surface_contract import (
    DEFAULT_IGNORE_JSON_KEYS,
    is_ignored_runtime_artifact,
    resolve_packaging_contract,
)

try:
    from vgo_contracts.mirror_topology_contract import resolve_mirror_topology_targets as _contract_resolve_mirror_targets
except ImportError:  # contracts helper may be added later in the release train
    _contract_resolve_mirror_targets = None

@dataclass(slots=True)
class GovernanceContext:
    repo_root: Path
    governance_path: Path
    governance: dict[str, Any]
    canonical_root: Path
    packaging: dict[str, Any]
    runtime_config: dict[str, Any]
    mirror_targets: list[dict[str, Any]]


def to_posix(path: Path | str) -> str:
    return Path(path).as_posix()


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


def relative_file_list(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        to_posix(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and not is_ignored_runtime_artifact(path.relative_to(root))
    )



def _mirror_topology_targets_fallback(governance: dict[str, Any]) -> list[dict[str, Any]]:
    topology = governance.get("mirror_topology") or {}
    targets = list(topology.get("targets") or [])
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
        target_id = str(target.get("id") or "").strip()
        target_path = str(target.get("path") or "").replace("\\", "/").strip()
        if not target_id or not target_path:
            continue
        normalized.append(
            {
                "id": target_id,
                "path": target_path,
                "role": str(target.get("role") or "mirror").strip() or "mirror",
            }
        )
    return normalized


def _attach_full_paths(targets: list[dict[str, Any]], repo_root: Path) -> list[dict[str, Any]]:
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


def mirror_topology_targets(governance: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    if _contract_resolve_mirror_targets is not None:
        raw_targets = _contract_resolve_mirror_targets(governance)
    else:
        raw_targets = _mirror_topology_targets_fallback(governance)
    return _attach_full_paths(raw_targets, repo_root)


def merge_runtime_config(governance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    return merge_installed_runtime_config(governance, defaults)


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
