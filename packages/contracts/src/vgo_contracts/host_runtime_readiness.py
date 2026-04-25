from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .adapter_registry_support import load_adapter_registry
from .canonical_vibe_contract import resolve_canonical_vibe_contract

REPO_ROOT = Path(__file__).resolve().parents[4]

DIRECT_RUNTIME_EXECUTABLES: dict[str, dict[str, str]] = {
    "codex": {
        "invocation_kind": "direct",
        "executable_env": "VGO_CODEX_EXECUTABLE",
        "command": "codex",
    }
}


def _resolve_repo_root(repo_root: str | Path | None) -> Path:
    """Resolve the repo root used for registry and policy lookups."""
    if repo_root is None:
        return REPO_ROOT
    return Path(repo_root).resolve()


def _resolve_executable_candidate(raw: str) -> str | None:
    """Resolve a command or file path to an executable file path."""
    candidate = str(raw or "").strip()
    if not candidate:
        return None
    resolved = shutil.which(candidate)
    if resolved:
        return str(Path(resolved).resolve())
    path_candidate = Path(candidate).expanduser()
    if path_candidate.is_file():
        return str(path_candidate.resolve())
    return None


def _fallback_canonical_vibe_contract(host_id: str | None) -> dict[str, Any]:
    """Return a safe bridged contract when canonical contract lookup fails."""
    normalized_host_id = str(host_id or "").strip().lower()
    return {
        "host_id": normalized_host_id,
        "entry_mode": "bridged_runtime",
        "fallback_policy": "blocked",
        "proof_required": True,
        "allow_skill_doc_fallback": False,
        "launcher_kind": "managed_bridge",
        "supports_bounded_stop": True,
    }


def _evaluate_direct_runtime(normalized_host_id: str) -> dict[str, Any]:
    """Evaluate whether a direct-runtime host executable is available."""
    descriptor = dict(DIRECT_RUNTIME_EXECUTABLES.get(normalized_host_id) or {})
    env_name = str(descriptor.get("executable_env") or "").strip()
    configured_command = str(descriptor.get("command") or "").strip()
    invocation_kind = str(descriptor.get("invocation_kind") or "").strip()
    env_value = str(os.environ.get(env_name) or "").strip() if env_name else ""
    resolved_path = None
    source = None
    command = configured_command

    if env_value:
        resolved_path = _resolve_executable_candidate(env_value)
        command = env_value
        if resolved_path:
            source = f"env:{env_name}"
    if resolved_path is None and configured_command:
        resolved_path = _resolve_executable_candidate(configured_command)
        if resolved_path:
            source = f"path:{configured_command}"

    return {
        "required": True,
        "ready": resolved_path is not None,
        "invocation_kind": invocation_kind or None,
        "executable_env": env_name or None,
        "command": command or None,
        "resolved_path": resolved_path,
        "source": source,
        "reason": (
            "direct_runtime_ready"
            if resolved_path is not None and invocation_kind == "direct"
            else f"direct_runtime_command_unavailable:{configured_command or normalized_host_id}"
        ),
    }


def _evaluate_bridge_runtime(contract: dict[str, Any], bridge_runtime_ready: bool) -> dict[str, Any]:
    """Evaluate the readiness of a managed or preview bridge surface."""
    launcher_kind = str(contract.get("launcher_kind") or "managed_bridge").strip() or "managed_bridge"
    return {
        "required": True,
        "ready": bool(bridge_runtime_ready),
        "launcher_kind": launcher_kind,
        "reason": f"{launcher_kind}_materialized" if bridge_runtime_ready else f"{launcher_kind}_missing",
    }


def evaluate_host_runtime_readiness(
    repo_root: str | Path | None,
    host_id: str | None,
    *,
    bridge_runtime_ready: bool | None = None,
    specialist_wrapper_ready: bool | None = None,
) -> dict[str, Any]:
    """Evaluate whether a host is truly ready for canonical vibe execution."""
    resolved_repo_root = _resolve_repo_root(repo_root)
    try:
        load_adapter_registry(resolved_repo_root)
        contract_repo_root: str | Path | None = resolved_repo_root
    except RuntimeError:
        contract_repo_root = REPO_ROOT
    try:
        contract = resolve_canonical_vibe_contract(contract_repo_root, host_id)
    except ValueError:
        contract = _fallback_canonical_vibe_contract(host_id)

    normalized_host_id = str(contract.get("host_id") or "").strip().lower()
    effective_bridge_ready = (
        bool(bridge_runtime_ready)
        if bridge_runtime_ready is not None
        else bool(specialist_wrapper_ready)
    )
    readiness_driver = "direct_runtime" if contract["entry_mode"] == "direct_runtime" else str(contract["launcher_kind"])
    direct_runtime: dict[str, Any] = {
        "required": False,
        "ready": False,
        "invocation_kind": None,
        "executable_env": None,
        "command": None,
        "resolved_path": None,
        "source": None,
        "reason": "not_applicable",
    }
    bridge_runtime: dict[str, Any] = {
        "required": contract["entry_mode"] != "direct_runtime",
        "ready": False,
        "launcher_kind": None,
        "reason": "not_applicable",
    }

    if readiness_driver == "direct_runtime":
        direct_runtime = _evaluate_direct_runtime(normalized_host_id)
        effective_runtime_ready = bool(direct_runtime["ready"])
    else:
        bridge_runtime = _evaluate_bridge_runtime(contract, effective_bridge_ready)
        effective_runtime_ready = bool(bridge_runtime["ready"])

    return {
        "host_id": normalized_host_id,
        "entry_mode": str(contract["entry_mode"]),
        "launcher_kind": str(contract["launcher_kind"]),
        "readiness_driver": readiness_driver,
        "specialist_wrapper_required": False,
        "specialist_wrapper_ready": False,
        "bridge_runtime": bridge_runtime,
        "effective_runtime_ready": bool(effective_runtime_ready),
        "recommended_host_closure_state": "closed_ready" if effective_runtime_ready else "configured_offline_unready",
        "direct_runtime": direct_runtime,
    }
