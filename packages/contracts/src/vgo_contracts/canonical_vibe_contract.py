from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter_registry_support import load_adapter_registry, resolve_adapter_entry

REPO_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_CANONICAL_VIBE_ENTRY_MODE = "bridged_runtime"
DEFAULT_CANONICAL_VIBE_FALLBACK_POLICY = "blocked"
DEFAULT_CANONICAL_VIBE_LAUNCHER_KIND = "managed_bridge"


def _resolve_repo_root(repo_root: str | Path | None) -> Path:
    if repo_root is None:
        return REPO_ROOT
    return Path(repo_root).resolve()


def _normalize_canonical_vibe_contract(raw: dict[str, Any], host_id: str | None) -> dict[str, Any]:
    host = str(host_id or "").strip().lower()
    entry_mode = str(raw.get("entry_mode") or DEFAULT_CANONICAL_VIBE_ENTRY_MODE).strip()
    launcher_kind = str(raw.get("launcher_kind") or DEFAULT_CANONICAL_VIBE_LAUNCHER_KIND).strip()
    fallback_policy = str(raw.get("fallback_policy") or DEFAULT_CANONICAL_VIBE_FALLBACK_POLICY).strip()
    normalized = {
        "host_id": host,
        "entry_mode": entry_mode,
        "fallback_policy": fallback_policy,
        "proof_required": bool(raw.get("proof_required", True)),
        "allow_skill_doc_fallback": bool(raw.get("allow_skill_doc_fallback", False)),
        "launcher_kind": launcher_kind,
        "supports_bounded_stop": bool(raw.get("supports_bounded_stop", True)),
    }
    if not normalized["entry_mode"]:
        raise ValueError(f"canonical_vibe entry_mode missing for host: {host_id}")
    if not normalized["fallback_policy"]:
        raise ValueError(f"canonical_vibe fallback_policy missing for host: {host_id}")
    if not normalized["launcher_kind"]:
        raise ValueError(f"canonical_vibe launcher_kind missing for host: {host_id}")
    return normalized


def resolve_canonical_vibe_contract(repo_root: str | Path | None, host_id: str | None) -> dict[str, Any]:
    registry = load_adapter_registry(_resolve_repo_root(repo_root))
    entry = resolve_adapter_entry(registry, host_id)
    raw = entry.get("canonical_vibe")
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"canonical_vibe contract missing for host: {host_id}")
    return _normalize_canonical_vibe_contract(raw, entry.get("id"))


def uses_skill_only_activation(
    host_id: str | None,
    *,
    repo_root: str | Path | None = None,
    start_path: str | Path | None = None,
) -> bool:
    resolved_repo_root = repo_root if repo_root is not None else start_path
    try:
        contract = resolve_canonical_vibe_contract(resolved_repo_root, host_id)
    except ValueError:
        return False
    return contract["entry_mode"] != "direct_runtime"
