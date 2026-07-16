from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys
import tempfile
from typing import Any
import warnings

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
POWERSHELL_HOST_POLICY_PATH = REPO_ROOT / "config" / "powershell-host-policy.json"
POWERSHELL_HOST_POLICY_DEFAULTS: dict[str, Any] = {
    "preferred_powershell_host": "pwsh",
    "require_pwsh_on_non_windows": True,
    "allow_windows_powershell_fallback": True,
    "record_host_resolution_artifacts": True,
}
SUPPORTED_POWERSHELL_HOSTS = frozenset({"pwsh", "windows-powershell"})
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.canonical_vibe_contract import resolve_canonical_vibe_contract
from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface
from vgo_contracts.entry_root_guard import EntryRootGuardError, resolve_entry_repo_root
from vgo_contracts.host_launch_receipt import HostLaunchReceipt, read_host_launch_receipt, write_host_launch_receipt
from vgo_runtime.kernel.loop import run_local_kernel
from vgo_runtime.powershell_bridge import run_powershell_json_command
from vgo_runtime.runtime_support import resolve_host_id
from vgo_runtime.runtime_truth import build_runtime_truth_packet, build_runtime_truth_packet_from_payload
from vgo_runtime.runtime_summary import (
    build_runtime_summary,
    build_runtime_summary_from_payload,
    refresh_runtime_summary_acceptance,
)
from vgo_runtime.stage_stop import (
    extract_terminal_stage as extract_shared_terminal_stage,
    resolve_progressive_stage_stop_source,
    resolve_stage_stop,
    resolve_terminal_stage,
)

RUNTIME_ENTRYPOINT_RELPATH = "scripts/runtime/invoke-vibe-runtime.ps1"
CANONICAL_ENTRY_BRIDGE_RELPATH = "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"
LOCAL_KERNEL_ENTRYPOINT_RELPATH = "packages/runtime-core/src/vgo_runtime/kernel/loop.py"
CANONICAL_RUNTIME_ENTRY_ID = "vibe"
CANONICAL_VIBE_PROGRESSIVE_STAGE_STOPS = ("requirement_doc", "xl_plan", "phase_cleanup")
MINIMUM_TRUTH_ARTIFACTS = {
    "runtime_input_packet": "runtime-input-packet.json",
    "governance_capsule": "governance-capsule.json",
    "stage_lineage": "stage-lineage.json",
}
REQUIRED_TRUTH_PACKET_FIELDS = (
    "module_assignments",
)
STRUCTURED_REENTRY_APPROVAL_ACTIONS: dict[str, frozenset[str]] = {
    "requirement_doc": frozenset(
        {
            "approve",
            "approve_requirement",
            "approve_requirement_doc",
            "approve_requirements",
        }
    ),
    "xl_plan": frozenset(
        {
            "approve",
            "approve_plan",
            "approve_execution_plan",
            "request_execute",
        }
    ),
}
STRUCTURED_REENTRY_REVISION_ACTIONS: dict[str, frozenset[str]] = {
    "requirement_doc": frozenset(
        {
            "revise",
            "request_changes",
            "request_revise",
            "revise_requirement",
            "revise_requirement_doc",
            "revise_requirements",
        }
    ),
    "xl_plan": frozenset(
        {
            "revise",
            "request_changes",
            "request_revise",
            "revise_plan",
            "revise_execution_plan",
            "revise_xl_plan",
        }
    ),
}
STRUCTURED_REENTRY_CONTROL_TOKENS = frozenset(
    {
        "approve",
        "approved",
        "approval",
        "approve requirement",
        "approve plan",
        "approve requirement doc",
        "approve execution plan",
        "request execute",
        "continue",
        "resume",
        "proceed",
        "continue plan",
        "continue execute",
        "继续",
        "继续执行",
        "继续规划",
        "继续计划",
        "继续实现",
        "批准",
        "批准继续",
        "批准继续计划",
        "批准继续执行",
        "同意",
        "按默认继续",
        "默认继续",
        "ok",
        "okay",
        "yes",
        "revise",
        "request changes",
        "request revise",
        "revise requirement",
        "revise plan",
        "修改",
        "修订",
        "修改需求",
        "修改计划",
    }
)


@dataclass(slots=True)
class CanonicalLaunchResult:
    """Structured result returned after a verified canonical vibe launch."""
    run_id: str
    session_root: Path
    summary_path: Path
    host_launch_receipt_path: Path
    launch_mode: str
    summary: dict[str, Any]
    artifacts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the launch result using JSON-friendly path strings."""
        payload = asdict(self)
        payload["session_root"] = str(self.session_root)
        payload["summary_path"] = str(self.summary_path)
        payload["host_launch_receipt_path"] = str(self.host_launch_receipt_path)
        payload["artifacts"] = dict(self.artifacts)
        return payload


# Backward-compatible alias for callers that imported the scaffold name.
CanonicalEntryResult = CanonicalLaunchResult


def _powershell_host_policy() -> dict[str, Any]:
    """Load the shared PowerShell host policy with strict field validation."""
    policy = dict(POWERSHELL_HOST_POLICY_DEFAULTS)
    try:
        raw_payload = POWERSHELL_HOST_POLICY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        warnings.warn(
            f"PowerShell host policy file not found: {POWERSHELL_HOST_POLICY_PATH}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy
    except OSError as exc:
        warnings.warn(
            f"Failed to read PowerShell host policy {POWERSHELL_HOST_POLICY_PATH}: {exc}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        warnings.warn(
            f"Invalid JSON in PowerShell host policy {POWERSHELL_HOST_POLICY_PATH}: {exc}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    if not isinstance(payload, dict):
        warnings.warn(
            f"PowerShell host policy {POWERSHELL_HOST_POLICY_PATH} must contain a JSON object; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    preferred_host = str(payload.get("preferred_powershell_host", "")).strip().lower()
    if preferred_host in SUPPORTED_POWERSHELL_HOSTS:
        policy["preferred_powershell_host"] = preferred_host
    elif preferred_host:
        warnings.warn(
            (
                f"Unsupported preferred_powershell_host in {POWERSHELL_HOST_POLICY_PATH}: "
                f"{preferred_host!r}; using default"
            ),
            RuntimeWarning,
            stacklevel=2,
        )
    for key in (
        "require_pwsh_on_non_windows",
        "allow_windows_powershell_fallback",
        "record_host_resolution_artifacts",
    ):
        if key in payload:
            if isinstance(payload[key], bool):
                policy[key] = payload[key]
            else:
                warnings.warn(
                    f"PowerShell host policy field {key} must be boolean; using default",
                    RuntimeWarning,
                    stacklevel=2,
                )
    return policy


def _is_windows_host() -> bool:
    """Return whether the current Python host is running on Windows."""
    return os.name == "nt"


def _resolve_powershell_host(*, return_diagnostics: bool = False) -> str | dict[str, Any] | None:
    """Resolve the PowerShell host path or return detailed search diagnostics."""
    policy = _powershell_host_policy()
    is_windows = _is_windows_host()
    prefer_pwsh = str(policy["preferred_powershell_host"]).strip().lower() == "pwsh"
    pwsh_candidates: list[tuple[str, str | None, str]] = [
        ("path-pwsh", shutil.which("pwsh"), "pwsh"),
        ("path-pwsh-exe", shutil.which("pwsh.exe"), "pwsh"),
    ]
    if is_windows:
        pwsh_candidates.extend(
            [
                ("default-pwsh", r"C:\Program Files\PowerShell\7\pwsh.exe", "pwsh"),
                ("preview-pwsh", r"C:\Program Files\PowerShell\7-preview\pwsh.exe", "pwsh"),
            ]
        )
    windows_powershell_candidates: list[tuple[str, str | None, str]] = []
    if is_windows:
        windows_powershell_candidates.extend(
            [
                ("path-powershell", shutil.which("powershell"), "windows-powershell"),
                ("path-powershell-exe", shutil.which("powershell.exe"), "windows-powershell"),
            ]
        )
    candidates: list[tuple[str, str | None, str]] = []
    if prefer_pwsh:
        candidates.extend(pwsh_candidates)
        if is_windows and policy["allow_windows_powershell_fallback"]:
            candidates.extend(windows_powershell_candidates)
    elif is_windows:
        candidates.extend(windows_powershell_candidates)

    checked: list[dict[str, Any]] = []
    for name, candidate, kind in candidates:
        resolved = str(Path(candidate)) if candidate else None
        exists = bool(resolved and Path(resolved).exists())
        is_file = bool(resolved and Path(resolved).is_file())
        checked.append(
            {
                "candidate_name": name,
                "candidate_kind": kind,
                "candidate_path": resolved,
                "exists": exists,
                "is_file": is_file,
            }
        )
        if exists and is_file:
            diagnostics = {
                "host_path": resolved,
                "host_kind": kind,
                "fallback_used": prefer_pwsh and kind == "windows-powershell",
                "candidates_checked": checked,
                "policy": policy,
            }
            return diagnostics if return_diagnostics else resolved

    if not is_windows and policy["require_pwsh_on_non_windows"]:
        diagnostics = {
            "host_path": None,
            "host_kind": None,
            "fallback_used": False,
            "candidates_checked": checked,
            "policy": policy,
            "error": "pwsh is required on non-Windows hosts",
        }
        return diagnostics if return_diagnostics else None

    diagnostics = {
        "host_path": None,
        "host_kind": None,
        "fallback_used": False,
        "candidates_checked": checked,
        "policy": policy,
    }
    return diagnostics if return_diagnostics else None


def _load_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    """Load a JSON object from disk and raise consistent runtime errors on failure."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object JSON in {label}: {path}")
    return payload


def _normalize_requested_entry_id(entry_id: str | None) -> str:
    """Collapse explicit entry hints onto the canonical runtime entry."""
    _ = str(entry_id or "").strip()
    return CANONICAL_RUNTIME_ENTRY_ID


def _runtime_entry_id_for_requested_entry(requested_entry_id: str) -> str:
    return requested_entry_id


def _seed_requested_stage_stop(
    requested_entry_id: str,
    requested_stage_stop: str | None,
) -> str | None:
    normalized_requested_stage_stop = str(requested_stage_stop or "").strip() or None
    return normalized_requested_stage_stop


def _continuation_sessions_root(artifact_root: Path) -> Path:
    return artifact_root / "outputs" / "runtime" / "vibe-sessions"


def _iter_runtime_summaries(artifact_root: Path) -> list[Path]:
    sessions_root = _continuation_sessions_root(artifact_root)
    if not sessions_root.exists():
        return []
    return sorted(
        (path for path in sessions_root.glob("*/runtime-summary.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _runtime_summary_path_for_run_id(artifact_root: Path, run_id: str | None) -> Path | None:
    candidate = str(run_id or "").strip()
    if not candidate or candidate in {".", ".."} or "/" in candidate or "\\" in candidate:
        return None
    windows_candidate = PureWindowsPath(candidate)
    if windows_candidate.drive or windows_candidate.anchor or windows_candidate.is_absolute():
        return None
    return _continuation_sessions_root(artifact_root) / candidate / "runtime-summary.json"


def _load_json_dict_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _artifact_paths(summary: dict[str, Any]) -> dict[str, Any]:
    artifacts = summary.get("artifacts") or {}
    return artifacts if isinstance(artifacts, dict) else {}


def _artifact_path_value(artifacts: dict[str, Any], key: str) -> str | None:
    value = artifacts.get(key)
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate or None


def _has_verified_host_launch_receipt(summary_path: Path) -> bool:
    receipt_path = summary_path.parent / "host-launch-receipt.json"
    try:
        receipt = read_host_launch_receipt(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    if str(receipt.launch_status or "").strip() != "verified":
        return False
    expected_run_id = summary_path.parent.name
    if expected_run_id and str(receipt.run_id or "").strip() != expected_run_id:
        return False
    return True


def _artifact_path_from_artifacts(artifacts: dict[str, Any], key: str, *, base_dir: Path | None = None) -> Path | None:
    raw_path = _artifact_path_value(artifacts, key)
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute() and base_dir is not None:
        candidate = base_dir / candidate
    return candidate


def _load_intent_contract_from_artifacts(
    artifacts: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    intent_contract_path = _artifact_path_from_artifacts(artifacts, "intent_contract", base_dir=base_dir)
    if intent_contract_path is None:
        return None
    return _load_json_dict_if_exists(intent_contract_path)


def _load_runtime_input_packet_from_summary(summary_path: Path | None) -> dict[str, Any] | None:
    """Best-effort load of the prior runtime packet from a bounded summary."""
    if summary_path is None or not summary_path.exists():
        return None
    summary = _load_json_dict_if_exists(summary_path)
    if not summary:
        return None

    candidate_paths: list[Path] = []
    artifacts = _artifact_paths(summary)
    runtime_packet_path = _artifact_path_value(artifacts, "runtime_input_packet")
    if runtime_packet_path:
        packet_path = Path(runtime_packet_path)
        if not packet_path.is_absolute():
            packet_path = (summary_path.parent / packet_path).resolve()
        candidate_paths.append(packet_path)
    candidate_paths.append((summary_path.parent / "runtime-input-packet.json").resolve())

    seen: set[Path] = set()
    for candidate_path in candidate_paths:
        if candidate_path in seen:
            continue
        seen.add(candidate_path)
        runtime_packet = _load_json_dict_if_exists(candidate_path)
        if runtime_packet:
            return runtime_packet
    return None


def _runtime_packet_task_type(runtime_packet: dict[str, Any] | None) -> str:
    if not isinstance(runtime_packet, dict):
        return ""
    route_snapshot = runtime_packet.get("route_snapshot")
    if isinstance(route_snapshot, dict):
        route_task_type = str(route_snapshot.get("task_type") or "").strip()
        if route_task_type:
            return route_task_type
    return ""


def _inherit_frozen_host_decision_fields_from_bounded_reentry(
    *,
    host_decision: dict[str, Any] | None,
    bounded_reentry: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Preserve frozen host decision fields across bounded re-entry."""
    decision = _normalize_host_decision(host_decision)
    if bounded_reentry is None:
        return decision

    summary_path_raw = str(bounded_reentry.get("summary_path") or "").strip()
    if not summary_path_raw:
        return decision

    runtime_packet = _load_runtime_input_packet_from_summary(Path(summary_path_raw))
    if not runtime_packet:
        return decision

    effective_decision = copy.deepcopy(decision) if decision else {}

    if effective_decision.get("code_task_tdd_decision") is None:
        prior_tdd_decision = runtime_packet.get("code_task_tdd_decision")
        if isinstance(prior_tdd_decision, dict):
            effective_decision["code_task_tdd_decision"] = copy.deepcopy(prior_tdd_decision)

    if effective_decision.get("phase_decomposition") is None:
        prior_phase_decomposition = None
        prior_host_decision = runtime_packet.get("host_decision")
        if isinstance(prior_host_decision, dict):
            prior_phase_decomposition = prior_host_decision.get("phase_decomposition")
        if prior_phase_decomposition is None:
            prior_phase_decomposition = runtime_packet.get("execution_phase_decomposition")
        if isinstance(prior_phase_decomposition, dict):
            effective_decision["phase_decomposition"] = copy.deepcopy(prior_phase_decomposition)

    governance_scope = str(runtime_packet.get("governance_scope") or "").strip()
    if not governance_scope:
        hierarchy = runtime_packet.get("hierarchy")
        if isinstance(hierarchy, dict):
            governance_scope = str(hierarchy.get("governance_scope") or "").strip()
    if (
        governance_scope.lower() == "root"
        and effective_decision.get("skill_execution_decision") is None
    ):
        prior_skill_execution_decision = runtime_packet.get("host_skill_execution_decision")
        if isinstance(prior_skill_execution_decision, dict):
            effective_decision["skill_execution_decision"] = copy.deepcopy(
                prior_skill_execution_decision
            )

    return effective_decision


def _normalize_prompt_token(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    lowered = lowered.strip("-")
    if len(lowered) > 64:
        lowered = lowered[:64].rstrip("-")
    return lowered


def _normalize_host_decision(host_decision: dict[str, Any] | None) -> dict[str, Any] | None:
    if host_decision is None:
        return None
    if not isinstance(host_decision, dict):
        raise RuntimeError("structured host decision must be a JSON object")
    return host_decision


def _parse_host_decision_json(
    host_decision_json: str | None,
    host_decision_json_file: str | None = None,
) -> dict[str, Any] | None:
    raw = str(host_decision_json or "").strip()
    file_path_text = str(host_decision_json_file or "").strip()
    if raw and file_path_text:
        raise RuntimeError("use either --host-decision-json or --host-decision-json-file, not both")
    if file_path_text:
        try:
            raw = Path(file_path_text).read_text(encoding="utf-8-sig").strip()
        except OSError as exc:
            raise RuntimeError("unable to read --host-decision-json-file") from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid JSON in --host-decision-json-file") from exc
        return _normalize_host_decision(payload)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("invalid JSON in --host-decision-json") from exc
    return _normalize_host_decision(payload)


def _serialize_host_decision_json(host_decision: dict[str, Any] | None) -> str | None:
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return None
    return json.dumps(decision, ensure_ascii=False, separators=(",", ":"))


def _requested_grade_floor_from_host_decision(
    host_decision: dict[str, Any] | None,
) -> str | None:
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return None

    for container in (
        decision,
        decision.get("continuation_context") if isinstance(decision.get("continuation_context"), dict) else None,
    ):
        if not isinstance(container, dict):
            continue
        for key in ("requested_grade_floor", "workflow_level"):
            value = str(container.get(key) or "").strip().upper()
            if value in {"L", "XL"}:
                return value
    return None


def _resolve_local_kernel_stage_stop_summary(
    *,
    entry_id: str,
    requested_stage_stop: str | None,
    has_agent_skill_organization: bool,
) -> tuple[str, str, str | None]:
    surface = load_discoverable_entry_surface(Path(__file__))
    discoverable_entry = surface.entry_by_id.get(entry_id)
    if discoverable_entry is None:
        raise RuntimeError(f"discoverable entry surface missing entry: {entry_id}")
    if not has_agent_skill_organization and requested_stage_stop in {"xl_plan", "plan_execute", "phase_cleanup"}:
        raise RuntimeError(f"agent_skill_organization is required before {requested_stage_stop}")
    default_stage_stop = discoverable_entry.requested_stage_stop if has_agent_skill_organization else "requirement_doc"
    stage_stop = resolve_stage_stop(
        requested_stage_stop,
        default_stage_stop,
        default_source="entry_surface_default",
    )
    return (
        stage_stop.effective_requested_stage_stop,
        stage_stop.stage_stop_source,
        stage_stop.requested_stage_stop,
    )


def _build_normal_reading_path(artifacts: dict[str, Any]) -> dict[str, Any]:
    proof_artifact_path = artifacts.get("work_dossier")
    proof_markdown_path = artifacts.get("work_dossier_markdown")
    artifact_paths = {
        "task_card": artifacts.get("task_card"),
        "work_plan": artifacts.get("work_plan"),
        "module_assignments": artifacts.get("module_assignments"),
        "work_results": artifacts.get("work_results"),
        "verification": artifacts.get("verification"),
        "proof": proof_artifact_path,
    }
    if proof_markdown_path:
        artifact_paths["proof_markdown"] = proof_markdown_path
    return {
        "reading_order": [
            "task_card",
            "work_plan",
            "module_assignments",
            "work_results",
            "verification",
            "proof",
        ],
        "artifact_paths": artifact_paths,
        "primary_artifact": "work_dossier",
        "primary_artifact_path": proof_artifact_path,
        "human_readable_artifact": "work_dossier_markdown",
        "human_readable_artifact_path": proof_markdown_path,
    }


def _resolve_canonical_stage_stop_source(
    *,
    requested_stage_stop: str | None,
    effective_requested_stage_stop: str | None,
) -> str:
    return resolve_progressive_stage_stop_source(
        requested_stage_stop=requested_stage_stop,
        effective_requested_stage_stop=effective_requested_stage_stop,
    )


def _resolve_canonical_terminal_stage(
    *,
    stage_lineage_payload: dict[str, Any],
    summary: dict[str, Any],
    effective_requested_stage_stop: str | None,
) -> str:
    return resolve_terminal_stage(
        stage_lineage_payload=stage_lineage_payload,
        summary=summary,
        fallback_terminal_stage=effective_requested_stage_stop,
    )


def _extract_continuation_keywords(intent_contract: dict[str, Any]) -> list[str]:
    keywords: list[str] = []

    goal = str(intent_contract.get("goal") or "").strip()
    if goal:
        keywords.append(goal)

    deliverable = str(intent_contract.get("deliverable") or "").strip()
    if deliverable and deliverable.lower() != "unknown":
        keywords.append(f"deliverable-{_normalize_prompt_token(deliverable)}")

    execution_mode = str(intent_contract.get("execution_mode") or "").strip()
    if execution_mode and execution_mode.lower() != "unspecified":
        keywords.append(f"mode-{_normalize_prompt_token(execution_mode)}")

    for prefix, values in (
        ("constraint", intent_contract.get("constraints") or []),
        ("capability", intent_contract.get("capabilities") or []),
    ):
        for value in values:
            token = _normalize_prompt_token(str(value))
            if token:
                keywords.append(f"{prefix}-{token}")

    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        if not keyword or keyword in seen:
            continue
        deduped.append(keyword)
        seen.add(keyword)
    return deduped


def _normalize_text_list(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def _host_decision_revision_delta(host_decision: dict[str, Any] | None) -> list[str]:
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return []

    for field_name in (
        "revision_delta",
        "requested_changes",
        "requested_change",
        "changes",
        "change_requests",
        "revision_notes",
    ):
        if field_name in decision:
            delta = _normalize_text_list(decision.get(field_name))
            if delta:
                return delta
    return []


def _is_control_only_structured_reentry_prompt(prompt_text: str) -> bool:
    normalized = _normalize_prompt_for_compare(prompt_text)
    if not normalized:
        return True
    if normalized in STRUCTURED_REENTRY_CONTROL_TOKENS:
        return True

    tokens = [token for token in normalized.split() if token]
    if tokens and len(tokens) <= 6 and all(token in STRUCTURED_REENTRY_CONTROL_TOKENS for token in tokens):
        return True

    compact = re.sub(r"\s+", "", normalized)
    if compact in {"批准", "继续", "同意", "批准继续", "批准继续计划", "批准继续执行"}:
        return True
    return False


def _build_structured_continuation_prompt(
    *,
    prompt_text: str,
    continuation: dict[str, Any],
) -> str:
    segments: list[str] = []

    goal = str(continuation.get("intent_goal") or "").strip()
    if goal:
        segments.append(goal)
    else:
        prior_task = str(continuation.get("task") or "").strip()
        if prior_task:
            segments.append(prior_task)

    revision_delta = _normalize_text_list(continuation.get("revision_delta"))
    if revision_delta:
        segments.append(f"Revision delta: {'; '.join(revision_delta)}.")

    delta = str(prompt_text or "").strip()
    if delta and not revision_delta and not _is_control_only_structured_reentry_prompt(delta):
        segments.append(f"Update: {delta}")

    return " ".join(segment for segment in segments if segment).strip() or delta


def _bounded_reentry_context_from_host_decision(
    host_decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return None
    raw_context = decision.get("continuation_context")
    if not isinstance(raw_context, dict):
        return None
    if not bool(raw_context.get("structured_bounded_reentry")):
        return None
    return raw_context


def _attach_bounded_continuation_context_to_host_decision(
    *,
    host_decision: dict[str, Any] | None,
    bounded_reentry: dict[str, Any] | None,
    prompt_text: str,
) -> dict[str, Any] | None:
    decision = _normalize_host_decision(host_decision)
    if not decision or not bounded_reentry:
        return decision
    if not _structured_host_decision_allows_bounded_reentry(
        decision,
        bounded_return_control=bounded_reentry,
    ):
        return decision

    reentry_action = str(bounded_reentry.get("structured_reentry_action") or "").strip() or None
    revision_delta = _normalize_text_list(bounded_reentry.get("revision_delta"))
    enriched = copy.deepcopy(decision)
    enriched["continuation_context"] = {
        "structured_bounded_reentry": True,
        "reentry_action": reentry_action,
        "source_run_id": str(bounded_reentry.get("source_run_id") or "").strip() or None,
        "terminal_stage": str(bounded_reentry.get("terminal_stage") or "").strip() or None,
        "next_stage": str(bounded_reentry.get("next_stage") or "").strip() or None,
        "revision_target_stage": str(bounded_reentry.get("revision_target_stage") or "").strip() or None,
        "revision_delta": revision_delta,
        "prior_task": str(bounded_reentry.get("task") or "").strip() or None,
        "prior_task_type": str(bounded_reentry.get("prior_task_type") or "").strip() or None,
        "prior_goal": str(bounded_reentry.get("intent_goal") or "").strip() or None,
        "prior_deliverable": str(bounded_reentry.get("intent_deliverable") or "").strip() or None,
        "prior_constraints": _normalize_text_list(bounded_reentry.get("intent_constraints")),
        "control_only_prompt": _is_control_only_structured_reentry_prompt(prompt_text),
    }
    return enriched


def _has_discoverable_entry_surface_candidate(start_path: Path) -> bool:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    while True:
        if (current / "config" / "vibe-entry-surfaces.json").exists():
            return True
        if current.parent == current:
            return False
        current = current.parent


def _progressive_stage_stops(repo_root: Path, entry_id: str) -> tuple[str, ...]:
    try:
        surface = load_discoverable_entry_surface(repo_root)
    except RuntimeError:
        if _has_discoverable_entry_surface_candidate(repo_root):
            raise
        if entry_id == CANONICAL_RUNTIME_ENTRY_ID:
            return CANONICAL_VIBE_PROGRESSIVE_STAGE_STOPS
        return ()
    entry = surface.entry_by_id.get(entry_id)
    if entry is not None:
        return tuple(entry.progressive_stage_stops)
    if entry_id == CANONICAL_RUNTIME_ENTRY_ID:
        raise RuntimeError("canonical vibe entry is missing from discoverable entry surface")
    return ()


def _resolve_progressive_requested_stage_stop(
    *,
    repo_root: Path,
    entry_id: str,
    requested_stage_stop: str | None,
    bounded_reentry: dict[str, Any] | None,
) -> str | None:
    normalized_requested_stage_stop = str(requested_stage_stop or "").strip() or None
    progressive_stage_stops = _progressive_stage_stops(repo_root, entry_id)
    if not progressive_stage_stops:
        return normalized_requested_stage_stop

    if bounded_reentry:
        terminal_stage = str(bounded_reentry.get("terminal_stage") or "").strip()
        if terminal_stage in progressive_stage_stops:
            if str(bounded_reentry.get("structured_reentry_action") or "").strip().lower() == "revise":
                return terminal_stage
            terminal_index = progressive_stage_stops.index(terminal_stage)
            if terminal_index + 1 < len(progressive_stage_stops):
                return progressive_stage_stops[terminal_index + 1]
            return terminal_stage

    if normalized_requested_stage_stop and normalized_requested_stage_stop in progressive_stage_stops[:-1]:
        return normalized_requested_stage_stop

    return progressive_stage_stops[0]


def _required_continuation_artifact(
    *,
    entry_id: str,
    bounded_reentry: dict[str, Any] | None,
) -> str | None:
    if entry_id != CANONICAL_RUNTIME_ENTRY_ID or bounded_reentry is None:
        return None

    terminal_stage = str(bounded_reentry.get("terminal_stage") or "").strip()
    if terminal_stage == "requirement_doc":
        return "requirement_doc"
    if terminal_stage == "xl_plan":
        return "execution_plan"
    return None


def _should_apply_continuation(
    entry_id: str,
    prompt_text: str,
    *,
    bounded_reentry: dict[str, Any] | None = None,
) -> bool:
    if bounded_reentry is not None:
        return _required_continuation_artifact(entry_id=entry_id, bounded_reentry=bounded_reentry) is not None
    return False


def _find_continuation_context(
    *,
    artifact_root: Path,
    required_artifact: str,
    run_id: str | None,
    preferred_run_id: str | None = None,
    allow_bounded_preferred: bool = False,
) -> dict[str, Any] | None:
    preferred_summary = _runtime_summary_path_for_run_id(artifact_root, preferred_run_id)
    bounded_preferred_locked = allow_bounded_preferred and bool(str(preferred_run_id or "").strip())
    if bounded_preferred_locked and (preferred_summary is None or not preferred_summary.is_file()):
        return None
    if preferred_summary and preferred_summary.is_file():
        preferred_summary_payload = _load_json_dict_if_exists(preferred_summary)
        preferred_is_bounded = bool(preferred_summary_payload) and _has_explicit_bounded_return_control(
            preferred_summary_payload
        )
        if not preferred_is_bounded or allow_bounded_preferred:
            continuation = _load_continuation_context_from_summary(
                preferred_summary,
                required_artifact=required_artifact,
            )
            if continuation:
                return continuation
            if bounded_preferred_locked:
                return None

    for summary_path in _iter_runtime_summaries(artifact_root):
        if run_id and summary_path.parent.name == run_id:
            continue
        summary = _load_json_dict_if_exists(summary_path)
        if not summary:
            continue
        if _has_explicit_bounded_return_control(summary):
            # Bounded wrapper stops must not be reused implicitly as continuation context.
            continue
        continuation = _load_continuation_context_from_summary(
            summary_path,
            required_artifact=required_artifact,
        )
        if continuation:
            return continuation
    return None


def _build_continuation_prompt(*, prompt_text: str, entry_id: str, continuation: dict[str, Any]) -> str:
    keywords = [f"continue-{entry_id}", *(_extract_continuation_keywords(continuation["intent_contract"]))]
    delta = prompt_text.strip()
    if delta:
        keywords.append(delta)
    return " ".join(part for part in keywords if part).strip()


def _normalize_prompt_for_compare(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", str(text or "").strip().lower())
    return " ".join(part for part in normalized.split() if part)


def _load_continuation_context_from_summary(
    summary_path: Path,
    *,
    required_artifact: str,
) -> dict[str, Any] | None:
    summary = _load_json_dict_if_exists(summary_path)
    if not summary:
        return None
    if not _has_verified_host_launch_receipt(summary_path):
        return None
    artifacts = _artifact_paths(summary)
    required_path = _artifact_path_from_artifacts(artifacts, required_artifact, base_dir=summary_path.parent)
    if not required_path or not required_path.exists():
        return None
    intent_contract = _load_intent_contract_from_artifacts(artifacts, base_dir=summary_path.parent)
    if not intent_contract:
        return None
    runtime_packet = _load_runtime_input_packet_from_summary(summary_path)
    return {
        "summary_path": str(summary_path),
        "run_id": str(summary.get("run_id") or summary_path.parent.name),
        "terminal_stage": str(summary.get("terminal_stage") or ""),
        "required_artifact": str(required_path),
        "task": str(summary.get("task") or ""),
        "prior_task_type": _runtime_packet_task_type(runtime_packet),
        "intent_contract": intent_contract,
        "intent_goal": str(intent_contract.get("goal") or "").strip(),
        "intent_deliverable": str(intent_contract.get("deliverable") or "").strip(),
        "intent_constraints": _normalize_text_list(intent_contract.get("constraints")),
    }


def _resolve_effective_prompt(
    *,
    host_id: str,
    entry_id: str,
    prompt: str,
    host_decision: dict[str, Any] | None = None,
    artifact_root: Path | None = None,
    run_id: str | None = None,
    bounded_reentry: dict[str, Any] | None = None,
    continuation_source_run_id: str | None = None,
    allow_bounded_preferred_source: bool = False,
) -> str:
    """Derive the runtime prompt, including bounded continuation context."""
    prompt_text = str(prompt or "")
    required_artifact = _required_continuation_artifact(entry_id=entry_id, bounded_reentry=bounded_reentry)
    if artifact_root is not None and required_artifact and _should_apply_continuation(
        entry_id,
        prompt_text,
        bounded_reentry=bounded_reentry,
    ):
        continuation = _find_continuation_context(
            artifact_root=artifact_root,
            required_artifact=required_artifact,
            run_id=run_id,
            preferred_run_id=continuation_source_run_id,
            allow_bounded_preferred=allow_bounded_preferred_source,
        )
        if continuation:
            structured_context = _bounded_reentry_context_from_host_decision(host_decision)
            if structured_context:
                continuation = dict(continuation)
                continuation["reentry_action"] = structured_context.get("reentry_action")
                continuation["revision_delta"] = _normalize_text_list(structured_context.get("revision_delta"))
                return _build_structured_continuation_prompt(
                    prompt_text=prompt_text,
                    continuation=continuation,
                )
            return _build_continuation_prompt(prompt_text=prompt_text, entry_id=entry_id, continuation=continuation)

    return prompt_text


def _coerce_bounded_return_control(summary: dict[str, Any], summary_path: Path | None = None) -> dict[str, Any] | None:
    if not _has_explicit_bounded_return_control(summary):
        return None

    raw = summary.get("bounded_return_control")
    if not isinstance(raw, dict):
        return None

    token = str(raw.get("reentry_token") or "").strip()
    source_run_id = str(raw.get("source_run_id") or summary.get("run_id") or "").strip()
    terminal_stage = str(raw.get("terminal_stage") or summary.get("terminal_stage") or "").strip()
    allowed_followup = [
        str(entry).strip()
        for entry in (raw.get("allowed_followup_entry_ids") or [])
        if str(entry).strip()
    ]
    if not token or not source_run_id or not terminal_stage or not allowed_followup:
        return None

    artifacts = _artifact_paths(summary)
    summary_base_dir = summary_path.parent if summary_path is not None else None
    if summary_base_dir is None and summary.get("summary_path"):
        summary_base_dir = Path(str(summary.get("summary_path"))).parent
    intent_contract = _load_intent_contract_from_artifacts(artifacts, base_dir=summary_base_dir)
    runtime_packet_path = _artifact_path_from_artifacts(artifacts, "runtime_input_packet", base_dir=summary_base_dir)
    runtime_packet = _load_json_dict_if_exists(runtime_packet_path) if runtime_packet_path else {}
    return {
        "summary_path": str(summary_path or summary.get("summary_path") or ""),
        "source_run_id": source_run_id,
        "terminal_stage": terminal_stage,
        "next_stage": str(raw.get("next_stage") or "").strip(),
        "allowed_followup_entry_ids": allowed_followup,
        "reentry_token": token,
        "task": str(summary.get("task") or ""),
        "intent_goal": str(intent_contract.get("goal") or "") if intent_contract else "",
        "intent_deliverable": str(intent_contract.get("deliverable") or "") if intent_contract else "",
        "intent_constraints": _normalize_text_list(intent_contract.get("constraints")) if intent_contract else [],
        "prior_task_type": _runtime_packet_task_type(runtime_packet),
    }


def _has_explicit_bounded_return_control(summary: dict[str, Any]) -> bool:
    raw = summary.get("bounded_return_control")
    return isinstance(raw, dict) and bool(raw.get("explicit_user_reentry_required"))


def _build_malformed_bounded_return_control(summary: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    artifacts = _artifact_paths(summary)
    intent_contract = _load_intent_contract_from_artifacts(artifacts, base_dir=summary_path.parent)
    runtime_packet_path = _artifact_path_from_artifacts(artifacts, "runtime_input_packet", base_dir=summary_path.parent)
    runtime_packet = _load_json_dict_if_exists(runtime_packet_path) if runtime_packet_path else {}
    return {
        "summary_path": str(summary_path),
        "source_run_id": str(summary.get("run_id") or summary_path.parent.name),
        "terminal_stage": str(summary.get("terminal_stage") or ""),
        "next_stage": "",
        "allowed_followup_entry_ids": [],
        "reentry_token": "",
        "task": str(summary.get("task") or ""),
        "intent_goal": str(intent_contract.get("goal") or "") if intent_contract else "",
        "intent_deliverable": str(intent_contract.get("deliverable") or "") if intent_contract else "",
        "intent_constraints": _normalize_text_list(intent_contract.get("constraints")) if intent_contract else [],
        "prior_task_type": _runtime_packet_task_type(runtime_packet),
        "malformed": True,
    }


def _find_latest_bounded_return_control(
    *,
    artifact_root: Path,
    run_id: str | None,
    preferred_run_id: str | None = None,
) -> dict[str, Any] | None:
    preferred_summary_path = _runtime_summary_path_for_run_id(artifact_root, preferred_run_id)
    if preferred_summary_path and preferred_summary_path.is_file():
        if not _has_verified_host_launch_receipt(preferred_summary_path):
            return None
        preferred_summary = _load_json_dict_if_exists(preferred_summary_path)
        if preferred_summary and _has_explicit_bounded_return_control(preferred_summary):
            preferred_guard = _coerce_bounded_return_control(preferred_summary, preferred_summary_path)
            if preferred_guard:
                preferred_guard["summary_path"] = str(preferred_summary_path)
                return preferred_guard
            return _build_malformed_bounded_return_control(preferred_summary, preferred_summary_path)

    for summary_path in _iter_runtime_summaries(artifact_root):
        if run_id and summary_path.parent.name == run_id:
            continue
        if not _has_verified_host_launch_receipt(summary_path):
            continue
        summary = _load_json_dict_if_exists(summary_path)
        if not summary:
            continue
        if not _has_explicit_bounded_return_control(summary):
            continue
        guard = _coerce_bounded_return_control(summary, summary_path)
        if guard:
            guard["summary_path"] = str(summary_path)
            return guard
        return _build_malformed_bounded_return_control(summary, summary_path)
    return None


def _looks_like_generic_reentry_prompt(
    prompt_text: str,
    *,
    bounded_return_control: dict[str, Any],
) -> bool:
    normalized_prompt = _normalize_prompt_for_compare(prompt_text)
    if not normalized_prompt:
        return True

    for prior_text in (
        str(bounded_return_control.get("task") or ""),
        str(bounded_return_control.get("intent_goal") or ""),
    ):
        normalized_prior = _normalize_prompt_for_compare(prior_text)
        if normalized_prior and normalized_prompt == normalized_prior:
            return True

    lowered_prompt = str(prompt_text or "").strip().lower()
    continuation_prefixes = (
        "continue",
        "resume",
        "proceed",
        "continue-",
        "execute plan",
        "execute the plan",
        "implement plan",
        "implement the plan",
        "finish plan",
        "finish the plan",
        "resume plan",
        "continue plan",
        "继续",
        "接着",
        "执行计划",
        "按计划执行",
        "继续执行",
        "继续规划",
        "继续实现",
    )
    for prefix in continuation_prefixes:
        if lowered_prompt == prefix:
            return True
        if prefix.endswith("-"):
            if lowered_prompt.startswith(prefix):
                return True
            continue
        if lowered_prompt.startswith(prefix + " "):
            return True

    return False


def _structured_host_decision_allows_bounded_reentry(
    host_decision: dict[str, Any] | None,
    *,
    bounded_return_control: dict[str, Any],
) -> bool:
    return _structured_host_decision_reentry_action(
        host_decision,
        bounded_return_control=bounded_return_control,
    ) is not None


def _structured_host_decision_reentry_action(
    host_decision: dict[str, Any] | None,
    *,
    bounded_return_control: dict[str, Any],
) -> str | None:
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return None

    terminal_stage = str(bounded_return_control.get("terminal_stage") or "").strip()
    if not terminal_stage:
        return None

    allowed_actions = STRUCTURED_REENTRY_APPROVAL_ACTIONS.get(terminal_stage)
    revision_actions = STRUCTURED_REENTRY_REVISION_ACTIONS.get(terminal_stage)
    if not allowed_actions and not revision_actions:
        return None

    decision_kind = str(decision.get("decision_kind") or "").strip().lower()
    decision_action = str(decision.get("decision_action") or "").strip().lower()
    approval_decision = str(decision.get("approval_decision") or "").strip().lower()

    if allowed_actions and decision_action in allowed_actions:
        return "approve"
    if decision_kind == "approval_response" and decision_action == "approve":
        return "approve"
    if approval_decision == "approve":
        return "approve"
    if revision_actions and decision_action in revision_actions:
        return "revise"
    return None


def _validate_bounded_reentry(
    *,
    artifact_root: Path | None,
    entry_id: str,
    prompt: str,
    run_id: str | None,
    continue_from_run_id: str | None,
    bounded_reentry_token: str | None,
    host_decision: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    provided_run_id = str(continue_from_run_id or "").strip()
    provided_token = str(bounded_reentry_token or "").strip()
    explicit_reentry_credentials_supplied = bool(provided_run_id or provided_token)
    if artifact_root is None:
        if explicit_reentry_credentials_supplied:
            raise RuntimeError(
                "bounded wrapper continuation credentials were provided but no matching bounded run could be found; "
                "verify --continue-from-run-id, --bounded-reentry-token, and artifact root"
            )
        return None

    prior_guard = _find_latest_bounded_return_control(
        artifact_root=artifact_root,
        run_id=run_id,
        preferred_run_id=continue_from_run_id,
    )
    if not prior_guard:
        if explicit_reentry_credentials_supplied:
            raise RuntimeError(
                "bounded wrapper continuation credentials were provided but no matching bounded run could be found; "
                "verify --continue-from-run-id, --bounded-reentry-token, and artifact root"
            )
        return None
    fallback_prompt_reentry = _looks_like_generic_reentry_prompt(
        prompt,
        bounded_return_control=prior_guard,
    )
    if bool(prior_guard.get("malformed")):
        if explicit_reentry_credentials_supplied or fallback_prompt_reentry or host_decision is not None:
            raise RuntimeError(
                "bounded wrapper continuation metadata is malformed; rerun the prior bounded wrapper stage before re-entering"
            )
        return None
    if entry_id not in set(prior_guard["allowed_followup_entry_ids"]):
        if explicit_reentry_credentials_supplied:
            allowed = sorted(str(item) for item in prior_guard["allowed_followup_entry_ids"])
            raise RuntimeError(
                f"bounded wrapper continuation entry_id {entry_id!r} is not allowed; "
                f"expected one of {allowed}"
            )
        return None
    structured_reentry_action = _structured_host_decision_reentry_action(
        host_decision,
        bounded_return_control=prior_guard,
    )
    structured_reentry = structured_reentry_action is not None
    if host_decision is not None:
        looks_like_reentry = structured_reentry
    else:
        looks_like_reentry = fallback_prompt_reentry
    if not looks_like_reentry:
        if explicit_reentry_credentials_supplied:
            expected_stage = str(prior_guard.get("terminal_stage") or "pending_bounded_stop")
            if host_decision is not None:
                raise RuntimeError(
                    "structured host decision does not authorize bounded re-entry for "
                    f"{expected_stage}; send an explicit approval or revision decision for the pending governed stop"
                )
            raise RuntimeError(
                "prompt does not look like a bounded-wrapper continuation for "
                f"{expected_stage}; provide a continuation prompt or remove the explicit re-entry credentials"
            )
        return None
    revision_delta = _host_decision_revision_delta(host_decision)
    if structured_reentry_action == "revise" and not revision_delta:
        expected_stage = str(prior_guard.get("terminal_stage") or "pending_bounded_stop")
        raise RuntimeError(
            "structured revise decision for "
            f"{expected_stage} requires non-empty revision_delta"
        )

    if not provided_run_id or not provided_token:
        raise RuntimeError(
            "bounded wrapper continuation requires explicit re-entry credentials from the latest bounded run "
            f"({prior_guard['source_run_id']}); forward --continue-from-run-id and --bounded-reentry-token"
        )
    if provided_run_id != prior_guard["source_run_id"]:
        raise RuntimeError(
            "bounded wrapper continuation run mismatch; expected "
            f"{prior_guard['source_run_id']} but received {provided_run_id}"
        )
    if provided_token != prior_guard["reentry_token"]:
        raise RuntimeError("bounded wrapper continuation token mismatch")
    result = dict(prior_guard)
    if structured_reentry_action:
        result["structured_reentry_action"] = structured_reentry_action
        if structured_reentry_action == "revise":
            result["revision_target_stage"] = str(prior_guard.get("terminal_stage") or "").strip() or None
            result["revision_delta"] = revision_delta
    return result


def _new_run_id() -> str:
    """Generate a unique canonical launch run identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = os.urandom(4).hex()
    return f"{timestamp}-{suffix}"


def _resolve_path(base_root: Path, value: str | Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_root / path).resolve()


def _resolve_artifact_root(repo_root: Path, artifact_root: str | Path | None) -> Path:
    """Resolve the artifact root relative to the repository when needed."""
    if artifact_root in (None, ""):
        return (repo_root / ".vibeskills").resolve()
    return _resolve_path(repo_root, artifact_root)


def _resolve_canonical_roots(
    repo_root: Path,
    *,
    workspace_root: str | Path | None,
    artifact_root: str | Path | None,
) -> tuple[Path, Path]:
    if workspace_root not in (None, ""):
        resolved_workspace_root = _resolve_path(repo_root, workspace_root)
        if artifact_root in (None, ""):
            return resolved_workspace_root, (resolved_workspace_root / ".vibeskills").resolve()
        return resolved_workspace_root, _resolve_path(resolved_workspace_root, artifact_root)
    if artifact_root not in (None, ""):
        resolved_artifact_root = _resolve_artifact_root(repo_root, artifact_root)
        return resolved_artifact_root, resolved_artifact_root
    return repo_root.resolve(), (repo_root / ".vibeskills").resolve()


def _resolve_session_root(*, repo_root: Path, run_id: str, artifact_root: str | Path | None) -> Path:
    """Build the canonical session output directory for a run."""
    return (_resolve_artifact_root(repo_root, artifact_root) / "outputs" / "runtime" / "vibe-sessions" / run_id).resolve()


def invoke_vibe_runtime_entrypoint(
    *,
    repo_root: Path,
    host_id: str,
    entry_id: str,
    prompt: str,
    requested_stage_stop: str | None,
    requested_grade_floor: str | None,
    run_id: str | None,
    workspace_root: Path,
    artifact_root: str | Path | None,
    module_execution_json_file: str | Path | None = None,
    host_decision: dict[str, Any] | None = None,
    force_runtime_neutral: bool = False,
) -> dict[str, Any]:
    """Invoke the PowerShell canonical entry bridge and return its JSON payload."""
    if force_runtime_neutral:
        raise RuntimeError("canonical entry requires PowerShell runtime bridge")

    resolution = _resolve_powershell_host(return_diagnostics=True)
    if not isinstance(resolution, dict) or not resolution.get("host_path"):
        checked = []
        policy_error = ""
        if isinstance(resolution, dict):
            checked = [
                entry.get("candidate_path") or entry.get("candidate_name") or "<unknown>"
                for entry in resolution.get("candidates_checked", [])
            ]
            policy_error = str(resolution.get("error") or "").strip()
        searched = ", ".join(checked) if checked else "<none>"
        reason = f"{policy_error}; " if policy_error else ""
        raise RuntimeError(
            "PowerShell executable not found; "
            + reason
            + "locations searched (PATH and well-known install paths): "
            + searched
        )
    shell = str(resolution["host_path"])

    bridge_path = repo_root / CANONICAL_ENTRY_BRIDGE_RELPATH
    if not bridge_path.exists():
        raise RuntimeError(f"canonical entry bridge not found: {bridge_path}")

    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(bridge_path),
        "-Task",
        prompt,
        "-HostId",
        host_id,
        "-EntryId",
        entry_id,
    ]
    if requested_stage_stop:
        command.extend(["-RequestedStageStop", requested_stage_stop])
    if requested_grade_floor:
        command.extend(["-RequestedGradeFloor", requested_grade_floor])
    if run_id:
        command.extend(["-RunId", run_id])
    command.extend(["-WorkspaceRoot", str(workspace_root)])
    if artifact_root:
        command.extend(["-ArtifactRoot", str(Path(artifact_root))])
    if module_execution_json_file:
        command.extend(["-ModuleExecutionJsonFile", str(Path(module_execution_json_file))])
    serialized_host_decision = _serialize_host_decision_json(host_decision)
    if serialized_host_decision:
        command.extend(["-HostDecisionJson", serialized_host_decision])

    bridge_output_path = Path(tempfile.gettempdir()) / f"vgo-canonical-entry-{os.getpid()}-{os.urandom(4).hex()}.json"
    command.extend(["-BridgeOutputJsonPath", str(bridge_output_path)])
    env = dict(os.environ)
    env["VCO_HOST_ID"] = host_id
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        return run_powershell_json_command(
            command,
            cwd=repo_root,
            bridge_label="canonical entry bridge",
            env=env,
            json_output_path=bridge_output_path,
        )
    finally:
        try:
            bridge_output_path.unlink()
        except FileNotFoundError:
            pass


def finalize_runtime_summary_payload(
    *,
    input_json_path: str | Path,
    output_json_path: str | Path,
) -> dict[str, Any]:
    """Build the Python-owned runtime summary from a staged payload file."""
    input_path = Path(input_json_path).resolve()
    output_path = Path(output_json_path).resolve()
    payload = _load_json_dict(input_path, label="runtime summary finalize payload")
    summary = build_runtime_summary_from_payload(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def refresh_runtime_summary_acceptance_payload(
    *,
    summary_json_path: str | Path,
    delivery_acceptance_report_json_path: str | Path,
    cleanup_receipt_path: str | Path,
) -> dict[str, Any]:
    summary_path = Path(summary_json_path).resolve()
    report_path = Path(delivery_acceptance_report_json_path).resolve()
    summary = _load_json_dict(summary_path, label="runtime-summary")
    report = _load_json_dict(report_path, label="delivery-acceptance-report")
    refreshed = refresh_runtime_summary_acceptance(
        summary,
        report,
        cleanup_receipt_path=str(Path(cleanup_receipt_path).resolve()),
        delivery_acceptance_report_path=str(report_path),
    )
    summary_path.write_text(json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return refreshed


def build_runtime_truth_payload(
    *,
    input_json_path: str | Path,
    output_json_path: str | Path,
) -> dict[str, Any]:
    """Build the Python-owned runtime truth packet from a staged payload file."""
    input_path = Path(input_json_path).resolve()
    output_path = Path(output_json_path).resolve()
    payload = _load_json_dict(input_path, label="runtime truth build payload")
    packet = build_runtime_truth_packet_from_payload(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return packet


def _launch_local_agent_kernel(
    *,
    repo_root: Path,
    workspace_root: Path,
    host_id: str,
    entry_id: str,
    prompt: str,
    requested_stage_stop: str | None,
    requested_grade_floor: str | None,
    run_id: str | None,
    local_agent_root: str | Path,
    summary_source: str,
    host_decision: dict[str, Any] | None,
) -> CanonicalLaunchResult:
    resolved_run_id = str(run_id or "").strip() or f"local-{_new_run_id()}"
    session_root = (Path(local_agent_root).expanduser().resolve() / "vibe" / "runs" / resolved_run_id).resolve()
    normalized_host_decision = _normalize_host_decision(host_decision)
    raw_agent_skill_organization = (
        normalized_host_decision.get("agent_skill_organization") if normalized_host_decision else None
    )
    agent_skill_organization = (
        dict(raw_agent_skill_organization) if isinstance(raw_agent_skill_organization, dict) else None
    )
    effective_requested_stage_stop, stage_stop_source, normalized_requested_stage_stop = _resolve_local_kernel_stage_stop_summary(
        entry_id=entry_id,
        requested_stage_stop=requested_stage_stop,
        has_agent_skill_organization=agent_skill_organization is not None,
    )
    should_execute = effective_requested_stage_stop in {"plan_execute", "phase_cleanup"}
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    receipt = HostLaunchReceipt(
        host_id=host_id,
        entry_id=CANONICAL_RUNTIME_ENTRY_ID,
        launch_mode="local-agent-kernel",
        launcher_path=str((repo_root / CANONICAL_ENTRY_BRIDGE_RELPATH).resolve()),
        requested_stage_stop=requested_stage_stop,
        requested_grade_floor=requested_grade_floor,
        runtime_entrypoint=str((repo_root / LOCAL_KERNEL_ENTRYPOINT_RELPATH).resolve()),
        run_id=resolved_run_id,
        created_at=created_at,
        launch_status="launched",
    )
    receipt_path = write_host_launch_receipt(session_root, receipt)

    try:
        kernel_result = run_local_kernel(
            agent_root=Path(local_agent_root),
            prompt=prompt,
            run_id=resolved_run_id,
            host_id=host_id,
            workspace_root=workspace_root,
            agent_skill_organization=agent_skill_organization,
            execute=should_execute,
        )
    except Exception:
        failed_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "failed"})
        write_host_launch_receipt(receipt_path, failed_receipt)
        raise

    artifacts = dict(kernel_result.get("artifacts") or {})
    if not artifacts:
        artifacts = {
            "work_dossier": str(session_root / "work-dossier.json"),
            "work_dossier_markdown": str(session_root / "work-dossier.md"),
            "task_card": str(session_root / "task-card.json"),
            "work_plan": str(session_root / "plan.json"),
            "plan": str(session_root / "plan.json"),
            "module_assignments": str(session_root / "module-assignments.json"),
            "work_results": str(session_root / "work-results.json"),
            "run_state": str(session_root / "run-state.json"),
            "verification": str(session_root / "verification.json"),
        }
    artifacts["host_launch_receipt"] = str(receipt_path)
    module_assignments_path = _artifact_path_from_artifacts(artifacts, "module_assignments")
    if module_assignments_path is None:
        raise RuntimeError("local agent kernel summary requires a module_assignments artifact")
    module_assignments = _load_json_dict(module_assignments_path, label="module-assignments")
    work_results_path = _artifact_path_from_artifacts(artifacts, "work_results")
    work_results = _load_json_dict(work_results_path, label="work-results") if work_results_path else {}
    verification_path = _artifact_path_from_artifacts(artifacts, "verification")
    verification = _load_json_dict(verification_path, label="verification") if verification_path else {}
    proof_ready = str(verification.get("result") or "") == "done"
    local_status = (
        "awaiting_agent_skill_organization"
        if agent_skill_organization is None
        else "completed"
        if proof_ready
        else "ready_for_execution"
        if not should_execute
        else "needs_execution"
    )
    artifact_kind = "delivery" if proof_ready else "scaffold"
    runtime_packet_path = session_root / MINIMUM_TRUTH_ARTIFACTS["runtime_input_packet"]
    governance_capsule_path = session_root / MINIMUM_TRUTH_ARTIFACTS["governance_capsule"]
    stage_lineage_path = session_root / MINIMUM_TRUTH_ARTIFACTS["stage_lineage"]
    runtime_packet = build_runtime_truth_packet(
        run_id=resolved_run_id,
        task=prompt,
        module_assignments=module_assignments,
        base_fields={
            "host_id": host_id,
            "entry_intent_id": entry_id,
            "requested_stage_stop": requested_stage_stop,
            "effective_requested_stage_stop": effective_requested_stage_stop,
            "stage_stop_source": stage_stop_source,
            "launch_mode": "local-agent-kernel",
            "status": local_status,
            "proof_ready": proof_ready,
            "artifact_kind": artifact_kind,
            "agent_skill_organization": agent_skill_organization,
            "skill_search_guide": {
                "schema_version": "skill_search_guide_v1",
                "skill_roots": list((kernel_result.get("skills_catalog") or {}).get("roots", [])),
                "search_protocol": [
                    "Split the task into modules before searching local skills.",
                    "Read candidate SKILL.md contracts before selecting an owner.",
                ],
                "selection_rules": [
                    "Only the Agent may select skills for module assignments.",
                    "Declare uncovered modules instead of fabricating coverage.",
                ],
                "disclosure_rules": [
                    "Requirement output exposes discovery guidance and candidates, not bound skills.",
                    "Execution output reports only skills selected by the Agent organization.",
                ],
            },
        },
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": list(kernel_result.get("candidates") or []),
            "rejected": [],
        },
    )
    runtime_packet_path.write_text(json.dumps(runtime_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    governance_capsule = {
        "runtime_selected_skill": CANONICAL_RUNTIME_ENTRY_ID,
        "host_id": host_id,
        "entry_id": entry_id,
        "launch_mode": "local-agent-kernel",
        "status": local_status,
        "proof_ready": proof_ready,
        "artifact_kind": artifact_kind,
    }
    governance_capsule_path.write_text(json.dumps(governance_capsule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stage_lineage = {
        "stages": [{"stage_name": effective_requested_stage_stop}],
        "last_stage_name": effective_requested_stage_stop,
        "status": local_status,
        "proof_ready": proof_ready,
        "artifact_kind": artifact_kind,
    }
    stage_lineage_path.write_text(json.dumps(stage_lineage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts["runtime_input_packet"] = str(runtime_packet_path)
    artifacts["governance_capsule"] = str(governance_capsule_path)
    artifacts["stage_lineage"] = str(stage_lineage_path)
    truth_artifacts = assert_minimum_truth_artifacts(session_root)
    assert_minimum_truth_consistency(
        receipt=receipt,
        runtime_packet_path=truth_artifacts["runtime_input_packet"],
        governance_capsule_path=truth_artifacts["governance_capsule"],
        stage_lineage_path=truth_artifacts["stage_lineage"],
    )
    summary = build_runtime_summary(
        run_id=resolved_run_id,
        task=prompt,
        artifacts=artifacts,
        module_assignments=module_assignments,
        base_fields={
            "launch_mode": "local-agent-kernel",
            "host_id": host_id,
            "entry_id": entry_id,
            "status": local_status,
            "proof_ready": proof_ready,
            "artifact_kind": artifact_kind,
            "requested_stage_stop": normalized_requested_stage_stop,
            "effective_requested_stage_stop": effective_requested_stage_stop,
            "stage_stop_source": stage_stop_source,
            "terminal_stage": effective_requested_stage_stop,
            "requested_grade_floor": requested_grade_floor,
            "summary_source": summary_source,
            "normal_reading_path": _build_normal_reading_path(artifacts),
        },
    )
    summary_path = session_root / "runtime-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "verified"})
    receipt_path = write_host_launch_receipt(receipt_path, verified_receipt)
    artifacts["host_launch_receipt"] = str(receipt_path)
    return CanonicalLaunchResult(
        run_id=resolved_run_id,
        session_root=session_root,
        summary_path=summary_path,
        host_launch_receipt_path=receipt_path,
        launch_mode=verified_receipt.launch_mode,
        summary=summary,
        artifacts=artifacts,
    )


def _looks_like_local_agent_root(path: Path) -> bool:
    resolved = path.resolve()
    return (resolved / "vibe" / "skills" / "local").is_dir()


def _auto_local_agent_root_candidate(
    *,
    repo_root: Path,
    artifact_root: str | Path | None,
) -> Path | None:
    candidates: list[Path] = []
    if artifact_root is not None:
        candidates.append(Path(artifact_root).expanduser())
    if repo_root.name.casefold() == "vibe" and (repo_root / "SKILL.md").is_file():
        candidates.append(repo_root.parent)
    candidates.append(repo_root)
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _looks_like_local_agent_root(resolved):
            return resolved
    return None


def _should_auto_use_local_agent_kernel(
    *,
    requested_entry_id: str,
    requested_stage_stop: str | None,
    requested_grade_floor: str | None,
    continue_from_run_id: str | None,
    bounded_reentry_token: str | None,
    host_decision: dict[str, Any] | None,
    local_agent_root_candidate: Path | None,
) -> bool:
    if requested_entry_id != CANONICAL_RUNTIME_ENTRY_ID:
        return False
    if local_agent_root_candidate is None:
        return False
    if requested_stage_stop or requested_grade_floor:
        return False
    if continue_from_run_id or bounded_reentry_token:
        return False
    if host_decision and not isinstance(host_decision.get("agent_skill_organization"), dict):
        return False
    return True


def assert_minimum_truth_artifacts(session_root: str | Path) -> dict[str, str]:
    """Verify that the minimum canonical truth artifacts exist for a session."""
    base = Path(session_root).resolve()
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for key, relpath in MINIMUM_TRUTH_ARTIFACTS.items():
        path = base / relpath
        if not path.exists():
            missing.append(str(path))
            continue
        resolved[key] = str(path)
    if missing:
        raise RuntimeError(f"Missing required runtime artifacts: {', '.join(missing)}")
    return resolved


def _load_runtime_truth_packet(
    runtime_packet_path: Path,
) -> dict[str, Any]:
    runtime_packet = _load_json_dict(runtime_packet_path, label="runtime-input-packet")
    module_assignments = runtime_packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        raise RuntimeError("canonical truth packet missing module_assignments object")

    raw_skill_routing = runtime_packet.get("skill_routing")
    if raw_skill_routing is not None and not isinstance(raw_skill_routing, dict):
        raise RuntimeError("canonical truth packet has malformed skill_routing object")
    return runtime_packet


def _extract_terminal_stage(stage_lineage: dict[str, Any]) -> str | None:
    return extract_shared_terminal_stage(stage_lineage)


def _module_assignments_bound_skill_ids(runtime_packet: dict[str, Any]) -> list[str]:
    module_assignments = runtime_packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        return []
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return []
    bound_skill_ids: list[str] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        skill_id = str(unit.get("bound_skill") or "").strip()
        if skill_id and skill_id not in bound_skill_ids:
            bound_skill_ids.append(skill_id)
    return bound_skill_ids


def assert_minimum_truth_consistency(
    *,
    receipt: HostLaunchReceipt,
    runtime_packet_path: str | Path,
    governance_capsule_path: str | Path,
    stage_lineage_path: str | Path,
) -> None:
    """Validate cross-artifact consistency for a canonical vibe launch."""
    runtime_packet = _load_json_dict(Path(runtime_packet_path), label="runtime-input-packet")
    missing_truth_fields = [field for field in REQUIRED_TRUTH_PACKET_FIELDS if field not in runtime_packet]
    if missing_truth_fields:
        missing = ", ".join(missing_truth_fields)
        raise RuntimeError(f"canonical truth packet missing required fields: {missing}")

    packet_requested_stop = runtime_packet.get("requested_stage_stop")
    if receipt.requested_stage_stop:
        if packet_requested_stop in (None, ""):
            raise RuntimeError("runtime packet dropped requested_stage_stop from canonical request")
        if str(packet_requested_stop) != receipt.requested_stage_stop:
            raise RuntimeError("requested_stage_stop mismatch between host launch receipt and runtime packet")

    packet_requested_grade_floor = runtime_packet.get("requested_grade_floor")
    if receipt.requested_grade_floor:
        if packet_requested_grade_floor in (None, ""):
            raise RuntimeError("runtime packet dropped requested_grade_floor from canonical request")
        if str(packet_requested_grade_floor) != receipt.requested_grade_floor:
            raise RuntimeError("requested_grade_floor mismatch between host launch receipt and runtime packet")

    canonical_router = runtime_packet.get("canonical_router")
    if isinstance(canonical_router, dict):
        _ = canonical_router.get("host_id")

    module_assignments = runtime_packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        raise RuntimeError("canonical truth packet missing module_assignments object")
    bound_skill_ids = _module_assignments_bound_skill_ids(runtime_packet)
    agent_organization = runtime_packet.get("agent_skill_organization")
    if agent_organization is None:
        if str(packet_requested_stop or "") in {"xl_plan", "plan_execute", "phase_cleanup"}:
            raise RuntimeError("canonical truth packet requires agent_skill_organization before planning or execution")
        if bound_skill_ids:
            raise RuntimeError("canonical truth packet cannot bind task skills before agent_skill_organization")
    elif not isinstance(agent_organization, dict):
        raise RuntimeError("canonical truth packet agent_skill_organization must be an object")
    else:
        modules = agent_organization.get("modules")
        if not isinstance(modules, list) or not modules:
            raise RuntimeError("canonical truth packet agent_skill_organization.modules must be a non-empty list")
        for module in modules:
            if not isinstance(module, dict):
                raise RuntimeError("canonical truth packet agent_skill_organization.modules must contain objects")
            module_id = str(module.get("module_id") or "").strip()
            criteria = module.get("acceptance_criteria")
            if not isinstance(criteria, list) or not criteria:
                raise RuntimeError(
                    f"canonical truth packet module {module_id} must include acceptance_criteria"
                )
            criterion_ids: set[str] = set()
            for criterion in criteria:
                if not isinstance(criterion, dict):
                    raise RuntimeError(
                        f"canonical truth packet module {module_id} acceptance_criteria must contain objects"
                    )
                criterion_id = str(criterion.get("criterion_id") or "").strip()
                description = str(criterion.get("description") or "").strip()
                verification_mode = str(criterion.get("verification_mode") or "").strip()
                if not criterion_id or not description:
                    raise RuntimeError(
                        f"canonical truth packet module {module_id} acceptance criteria require criterion_id and description"
                    )
                if criterion_id in criterion_ids:
                    raise RuntimeError(
                        f"canonical truth packet module {module_id} has duplicate acceptance criterion {criterion_id}"
                    )
                if verification_mode not in {"automated", "manual"}:
                    raise RuntimeError(
                        f"canonical truth packet module {module_id} acceptance criterion verification_mode must be automated or manual"
                    )
                criterion_ids.add(criterion_id)
        selected_rows = agent_organization.get("selected_skills")
        if not isinstance(selected_rows, list):
            raise RuntimeError("canonical truth packet agent_skill_organization.selected_skills must be a list")
        selected_skill_ids = sorted(
            {
                str(row.get("skill_id") or "").strip()
                for row in selected_rows
                if isinstance(row, dict) and str(row.get("skill_id") or "").strip()
            }
        )
        if selected_skill_ids != sorted(set(bound_skill_ids)):
            raise RuntimeError("canonical truth packet module_assignments must match agent_skill_organization selected skills")

    governance_capsule = _load_json_dict(Path(governance_capsule_path), label="governance-capsule")
    runtime_selected_skill = str(governance_capsule.get("runtime_selected_skill") or "").strip()
    if runtime_selected_skill != CANONICAL_RUNTIME_ENTRY_ID:
        raise RuntimeError("governance capsule must keep vibe as runtime authority")

    divergence_shadow = runtime_packet.get("divergence_shadow")
    if isinstance(divergence_shadow, dict):
        divergence_runtime_skill = str(divergence_shadow.get("runtime_selected_skill") or "").strip()
        if divergence_runtime_skill and divergence_runtime_skill != CANONICAL_RUNTIME_ENTRY_ID:
            raise RuntimeError("divergence_shadow must keep vibe as runtime authority when present")
    # divergence_shadow now only needs to preserve secondary mismatch/override
    # shadowing for older readers. Runtime authority truth stays with
    # governance-capsule.json, and the live selected-skill truth stays with
    # kernel-facing module_assignments evidence.

    stage_lineage = _load_json_dict(Path(stage_lineage_path), label="stage-lineage")
    stage_entries = stage_lineage.get("stages")
    if not (isinstance(stage_entries, list) and stage_entries):
        stage_entries = stage_lineage.get("entries")
    if not (isinstance(stage_entries, list) and stage_entries):
        raise RuntimeError("stage-lineage missing terminal stage")
    terminal_stage = _extract_terminal_stage(stage_lineage)
    if not terminal_stage:
        raise RuntimeError("stage-lineage missing terminal stage")
    if receipt.requested_stage_stop:
        handoff_path = Path(stage_lineage_path).resolve().parent / "agent-execution-handoff.json"
        handoff = (
            _load_json_dict(handoff_path, label="agent-execution-handoff")
            if handoff_path.exists()
            else {}
        )
        is_agent_handoff_stop = (
            receipt.requested_stage_stop == "phase_cleanup"
            and terminal_stage == "plan_execute"
            and handoff.get("status") == "agent_action_required"
            and handoff.get("control_owner") == "agent"
        )
        if terminal_stage != receipt.requested_stage_stop and not is_agent_handoff_stop:
            raise RuntimeError("bounded stop mismatch between host launch receipt and stage-lineage")


def launch_canonical_vibe(
    *,
    repo_root: str | Path,
    host_id: str | None,
    entry_id: str | None,
    prompt: str,
    requested_stage_stop: str | None = None,
    requested_grade_floor: str | None = None,
    run_id: str | None = None,
    workspace_root: str | Path | None = None,
    artifact_root: str | Path | None = None,
    local_agent_root: str | Path | None = None,
    continue_from_run_id: str | None = None,
    bounded_reentry_token: str | None = None,
    module_execution_json_file: str | Path | None = None,
    host_decision: dict[str, Any] | None = None,
    force_runtime_neutral: bool = False,
) -> CanonicalLaunchResult:
    """Launch canonical vibe, verify its artifacts, and return launch metadata."""
    decision = resolve_entry_repo_root(repo_root, script_anchor=Path(__file__))
    repo_root_path = decision.repo_root
    resolved_workspace_root, resolved_artifact_root = _resolve_canonical_roots(
        repo_root_path,
        workspace_root=workspace_root,
        artifact_root=artifact_root,
    )
    resolved_host_id = resolve_host_id(host_id)
    requested_entry_id = _normalize_requested_entry_id(entry_id)
    runtime_entry_id = _runtime_entry_id_for_requested_entry(requested_entry_id)
    requested_stage_stop_seed = _seed_requested_stage_stop(requested_entry_id, requested_stage_stop)
    if local_agent_root is not None:
        return _launch_local_agent_kernel(
            repo_root=repo_root_path,
            workspace_root=resolved_workspace_root,
            host_id=resolved_host_id,
            entry_id=runtime_entry_id,
            prompt=prompt,
            requested_stage_stop=requested_stage_stop_seed,
            requested_grade_floor=requested_grade_floor,
            run_id=run_id,
            local_agent_root=local_agent_root,
            summary_source="explicit local agent root delegation",
            host_decision=host_decision,
        )
    auto_local_agent_root = _auto_local_agent_root_candidate(
        repo_root=repo_root_path,
        artifact_root=resolved_artifact_root,
    )
    if _should_auto_use_local_agent_kernel(
        requested_entry_id=runtime_entry_id,
        requested_stage_stop=requested_stage_stop_seed,
        requested_grade_floor=requested_grade_floor,
        continue_from_run_id=continue_from_run_id,
        bounded_reentry_token=bounded_reentry_token,
        host_decision=host_decision,
        local_agent_root_candidate=auto_local_agent_root,
    ):
        return _launch_local_agent_kernel(
            repo_root=repo_root_path,
            workspace_root=resolved_workspace_root,
            host_id=resolved_host_id,
            entry_id=runtime_entry_id,
            prompt=prompt,
            requested_stage_stop=requested_stage_stop_seed,
            requested_grade_floor=requested_grade_floor,
            run_id=run_id,
            local_agent_root=auto_local_agent_root,
            summary_source="auto local agent root detection",
            host_decision=host_decision,
        )
    if module_execution_json_file is not None:
        return _launch_agent_execution_reentry(
            repo_root=repo_root_path,
            workspace_root=resolved_workspace_root,
            host_id=resolved_host_id,
            entry_id=runtime_entry_id,
            prompt=prompt,
            requested_stage_stop=requested_stage_stop_seed,
            requested_grade_floor=requested_grade_floor,
            run_id=run_id,
            artifact_root=resolved_artifact_root,
            continue_from_run_id=continue_from_run_id,
            bounded_reentry_token=bounded_reentry_token,
            module_execution_json_file=module_execution_json_file,
            host_decision=host_decision,
            force_runtime_neutral=force_runtime_neutral,
        )
    normalized_host_decision = _normalize_host_decision(host_decision)
    validated_reentry = _validate_bounded_reentry(
        artifact_root=resolved_artifact_root,
        entry_id=runtime_entry_id,
        prompt=prompt,
        run_id=run_id,
        continue_from_run_id=continue_from_run_id,
        bounded_reentry_token=bounded_reentry_token,
        host_decision=normalized_host_decision,
    )
    effective_host_decision = _inherit_frozen_host_decision_fields_from_bounded_reentry(
        host_decision=normalized_host_decision,
        bounded_reentry=validated_reentry,
    )
    effective_host_decision = _attach_bounded_continuation_context_to_host_decision(
        host_decision=effective_host_decision,
        bounded_reentry=validated_reentry,
        prompt_text=prompt,
    )
    effective_requested_stage_stop = _resolve_progressive_requested_stage_stop(
        repo_root=repo_root_path,
        entry_id=requested_entry_id,
        requested_stage_stop=requested_stage_stop_seed,
        bounded_reentry=validated_reentry,
    )
    effective_requested_grade_floor = requested_grade_floor or _requested_grade_floor_from_host_decision(
        effective_host_decision,
    )
    prompt_entry_id = runtime_entry_id if validated_reentry is not None else requested_entry_id
    effective_prompt = _resolve_effective_prompt(
        host_id=resolved_host_id,
        entry_id=prompt_entry_id,
        prompt=prompt,
        host_decision=effective_host_decision,
        artifact_root=resolved_artifact_root,
        run_id=run_id,
        bounded_reentry=validated_reentry,
        continuation_source_run_id=(str(validated_reentry["source_run_id"]) if validated_reentry else None),
        allow_bounded_preferred_source=bool(validated_reentry),
    )
    resolved_run_id = str(run_id or "").strip() or _new_run_id()
    session_root = _resolve_session_root(
        repo_root=repo_root_path,
        run_id=resolved_run_id,
        artifact_root=resolved_artifact_root,
    )
    summary_path = (session_root / "runtime-summary.json").resolve()
    receipt = HostLaunchReceipt(
        host_id=resolved_host_id,
        entry_id=CANONICAL_RUNTIME_ENTRY_ID,
        launch_mode="canonical-entry",
        launcher_path=str((repo_root_path / CANONICAL_ENTRY_BRIDGE_RELPATH).resolve()),
        requested_stage_stop=effective_requested_stage_stop,
        requested_grade_floor=effective_requested_grade_floor,
        runtime_entrypoint=str((repo_root_path / RUNTIME_ENTRYPOINT_RELPATH).resolve()),
        run_id=resolved_run_id,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        launch_status="launched",
    )
    receipt_path = write_host_launch_receipt(session_root, receipt)

    try:
        payload = invoke_vibe_runtime_entrypoint(
            repo_root=repo_root_path,
            host_id=resolved_host_id,
            entry_id=runtime_entry_id,
            prompt=effective_prompt,
            requested_stage_stop=effective_requested_stage_stop,
            requested_grade_floor=effective_requested_grade_floor,
            run_id=resolved_run_id,
            workspace_root=resolved_workspace_root,
            artifact_root=resolved_artifact_root,
            module_execution_json_file=None,
            host_decision=effective_host_decision,
            force_runtime_neutral=force_runtime_neutral,
        )
    except Exception:
        _mark_host_launch_failed(receipt_path, receipt)
        raise

    try:
        return _finalize_canonical_launch_result(
            receipt=receipt,
            receipt_path=receipt_path,
            requested_entry_id=requested_entry_id,
            requested_stage_stop=requested_stage_stop_seed,
            effective_requested_stage_stop=effective_requested_stage_stop,
            effective_prompt=effective_prompt,
            payload=payload,
            fallback_run_id=resolved_run_id,
            fallback_summary_path=summary_path,
        )
    except Exception:
        _mark_host_launch_failed(receipt_path, receipt)
        raise


def _launch_agent_execution_reentry(
    *,
    repo_root: Path,
    workspace_root: Path,
    host_id: str,
    entry_id: str,
    prompt: str,
    requested_stage_stop: str | None,
    requested_grade_floor: str | None,
    run_id: str | None,
    artifact_root: Path,
    continue_from_run_id: str | None,
    bounded_reentry_token: str | None,
    module_execution_json_file: str | Path,
    host_decision: dict[str, Any] | None,
    force_runtime_neutral: bool,
) -> CanonicalLaunchResult:
    source_run_id = str(continue_from_run_id or "").strip()
    if not source_run_id:
        raise RuntimeError("Agent execution re-entry requires --continue-from-run-id")
    if str(run_id or "").strip() not in {"", source_run_id}:
        raise RuntimeError("Agent execution re-entry must resume the source run")
    if bounded_reentry_token:
        raise RuntimeError("Agent execution re-entry does not accept a user approval token")
    if host_decision is not None:
        raise RuntimeError("Agent execution re-entry does not accept a host approval decision")

    session_root = _resolve_session_root(
        repo_root=repo_root,
        run_id=source_run_id,
        artifact_root=artifact_root,
    )
    runtime_packet = _load_runtime_truth_packet(session_root / "runtime-input-packet.json")
    frozen_task = str(runtime_packet.get("task") or "").strip()
    if not frozen_task:
        raise RuntimeError("Agent execution re-entry requires the frozen task from runtime-input-packet.json")
    handoff = _load_json_dict(session_root / "agent-execution-handoff.json", label="agent-execution-handoff")
    if handoff.get("status") != "agent_action_required" or handoff.get("control_owner") != "agent":
        raise RuntimeError("source run is not waiting for Agent execution results")

    submitted_path = Path(module_execution_json_file).expanduser().resolve()
    submitted = _load_json_dict(submitted_path, label="module-execution")
    _validate_agent_module_execution(
        session_root=session_root,
        source_run_id=source_run_id,
        handoff=handoff,
        submitted=submitted,
    )

    receipt = HostLaunchReceipt(
        host_id=host_id,
        entry_id=CANONICAL_RUNTIME_ENTRY_ID,
        launch_mode="canonical-entry",
        launcher_path=str((repo_root / CANONICAL_ENTRY_BRIDGE_RELPATH).resolve()),
        requested_stage_stop="phase_cleanup",
        requested_grade_floor=requested_grade_floor,
        runtime_entrypoint=str((repo_root / RUNTIME_ENTRYPOINT_RELPATH).resolve()),
        run_id=source_run_id,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        launch_status="launched",
    )
    receipt_path = write_host_launch_receipt(session_root, receipt)
    try:
        payload = invoke_vibe_runtime_entrypoint(
            repo_root=repo_root,
            host_id=host_id,
            entry_id=entry_id,
            prompt=frozen_task,
            requested_stage_stop="phase_cleanup",
            requested_grade_floor=requested_grade_floor,
            run_id=source_run_id,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            module_execution_json_file=submitted_path,
            host_decision=None,
            force_runtime_neutral=force_runtime_neutral,
        )
        return _finalize_canonical_launch_result(
            receipt=receipt,
            receipt_path=receipt_path,
            requested_entry_id=entry_id,
            requested_stage_stop=requested_stage_stop,
            effective_requested_stage_stop="phase_cleanup",
            effective_prompt=frozen_task,
            payload=payload,
            fallback_run_id=source_run_id,
            fallback_summary_path=session_root / "runtime-summary.json",
        )
    except Exception:
        _mark_host_launch_failed(receipt_path, receipt)
        raise


def _validate_agent_module_execution(
    *,
    session_root: Path,
    source_run_id: str,
    handoff: dict[str, Any],
    submitted: dict[str, Any],
) -> None:
    result_contract = handoff.get("result_contract")
    if not isinstance(result_contract, dict):
        raise RuntimeError("Agent execution handoff is missing result_contract")
    required_top_level_fields = result_contract.get("required_top_level_fields")
    if not isinstance(required_top_level_fields, list) or any(
        not isinstance(field, str) or not field.strip() for field in required_top_level_fields
    ):
        raise RuntimeError("Agent execution handoff result_contract required_top_level_fields is invalid")
    for field in required_top_level_fields:
        if field not in submitted:
            raise RuntimeError(f"module execution is missing required field: {field}")
    if submitted.get("schema_version") != "module_execution_v1":
        raise RuntimeError("Agent module execution must use module_execution_v1")
    if str(handoff.get("source_run_id") or "") != source_run_id:
        raise RuntimeError("Agent execution handoff source_run_id does not match the source run")
    if str(submitted.get("source_run_id") or "") != source_run_id:
        raise RuntimeError("module execution source_run_id does not match the handoff run")

    tdd_contract = result_contract.get("tdd_evidence")
    if tdd_contract is not None:
        if not isinstance(tdd_contract, dict):
            raise RuntimeError("Agent execution handoff TDD evidence contract is invalid")
        tdd_evidence = submitted.get("tdd_evidence")
        if not isinstance(tdd_evidence, dict):
            raise RuntimeError("module execution TDD evidence must be a JSON object")
        required_tdd_fields = tdd_contract.get("required_result_fields")
        if not isinstance(required_tdd_fields, list) or any(
            not isinstance(field, str) or not field.strip() for field in required_tdd_fields
        ):
            raise RuntimeError("Agent execution handoff TDD evidence required fields are invalid")
        for field in required_tdd_fields:
            if field not in tdd_evidence:
                raise RuntimeError(f"module execution TDD evidence is missing required field: {field}")

        tdd_state = str(tdd_evidence.get("state") or "")
        allowed_tdd_states = tdd_contract.get("terminal_states")
        if not isinstance(allowed_tdd_states, list) or tdd_state not in allowed_tdd_states:
            raise RuntimeError("module execution TDD evidence state must be passing, failing, or blocked")

        list_fields = (
            "evidence_paths",
            "red_phase_evidence_paths",
            "green_phase_evidence_paths",
            "refactor_phase_evidence_paths",
            "covered_code_task_tdd_evidence_requirements",
            "covered_code_task_tdd_exceptions",
        )
        for field in list_fields:
            value = tdd_evidence.get(field)
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise RuntimeError(f"module execution TDD evidence {field} must be a JSON array of strings")
        if not isinstance(tdd_evidence.get("notes"), str):
            raise RuntimeError("module execution TDD evidence notes must be a string")

        if tdd_state == "passing":
            required_tdd_requirements = tdd_contract.get(
                "required_code_task_tdd_evidence_requirements"
            )
            required_tdd_exceptions = tdd_contract.get("required_code_task_tdd_exceptions")
            if tdd_evidence["covered_code_task_tdd_evidence_requirements"] != required_tdd_requirements:
                raise RuntimeError(
                    "passing module execution TDD evidence must cover the frozen TDD requirements"
                )
            if tdd_evidence["covered_code_task_tdd_exceptions"] != required_tdd_exceptions:
                raise RuntimeError(
                    "passing module execution TDD evidence must cover the frozen TDD exceptions"
                )
            if not tdd_evidence["evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires evidence paths")
            if required_tdd_requirements and not tdd_evidence["red_phase_evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires red-phase evidence paths")
            if required_tdd_requirements and not tdd_evidence["green_phase_evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires green-phase evidence paths")

    plan_path = session_root / "module-work-plan.json"
    plan = _load_json_dict(plan_path, label="module-work-plan")
    if str(submitted.get("module_work_plan_digest") or "") != hashlib.sha256(plan_path.read_bytes()).hexdigest():
        raise RuntimeError("module execution does not match the approved module work plan digest")

    raw_submitted_units = submitted.get("units")
    if not isinstance(raw_submitted_units, list) or any(
        not isinstance(unit, dict) for unit in raw_submitted_units
    ):
        raise RuntimeError("module execution units must be a JSON array of objects")
    planned_units = {
        str(unit.get("unit_id") or ""): unit
        for unit in plan.get("work_units") or []
        if isinstance(unit, dict) and str(unit.get("unit_id") or "")
    }
    submitted_units = {
        str(unit.get("unit_id") or ""): unit
        for unit in raw_submitted_units
        if isinstance(unit, dict) and str(unit.get("unit_id") or "")
    }
    if set(submitted_units) != set(planned_units) or len(raw_submitted_units) != len(planned_units):
        raise RuntimeError("module execution work units must exactly match the approved plan")
    for unit_id, planned_unit in planned_units.items():
        unit = submitted_units[unit_id]
        for field in (
            "unit_id",
            "module_id",
            "skill_id",
            "role",
            "state",
            "result_summary",
            "evidence_paths",
            "verification_results",
        ):
            if field not in unit:
                raise RuntimeError(f"module execution unit {unit_id} is missing required field: {field}")
        if str(unit.get("module_id") or "") != str(planned_unit.get("module_id") or ""):
            raise RuntimeError(f"module execution unit {unit_id} changed its module binding")
        if (str(unit.get("skill_id") or "") or None) != (str(planned_unit.get("skill_id") or "") or None):
            raise RuntimeError(f"module execution unit {unit_id} changed its Skill binding")
        if str(unit.get("role") or "") != str(planned_unit.get("role") or ""):
            raise RuntimeError(f"module execution unit {unit_id} changed its role binding")
        state = str(unit.get("state") or "")
        if state not in {"completed", "failed", "blocked"}:
            raise RuntimeError(f"module execution unit {unit_id} is not terminal")
        if state == "completed" and not str(unit.get("result_summary") or "").strip():
            raise RuntimeError(f"completed module execution unit {unit_id} requires a result summary")

    raw_submitted_modules = submitted.get("modules")
    if not isinstance(raw_submitted_modules, list) or any(
        not isinstance(module, dict) for module in raw_submitted_modules
    ):
        raise RuntimeError("module execution modules must be a JSON array of objects")
    planned_modules = {
        str(module.get("module_id") or ""): module
        for module in plan.get("modules") or []
        if isinstance(module, dict) and str(module.get("module_id") or "")
    }
    submitted_modules = {
        str(module.get("module_id") or ""): module
        for module in raw_submitted_modules
        if isinstance(module, dict) and str(module.get("module_id") or "")
    }
    if set(submitted_modules) != set(planned_modules) or len(raw_submitted_modules) != len(planned_modules):
        raise RuntimeError("module execution modules must exactly match the approved plan")
    for module_id, planned_module in planned_modules.items():
        module = submitted_modules[module_id]
        for field in (
            "module_id",
            "required",
            "execution_mode",
            "gap_reason",
            "state",
            "criterion_results",
        ):
            if field not in module:
                raise RuntimeError(f"module execution module {module_id} is missing required field: {field}")
        if not isinstance(module.get("required"), bool) or module.get("required") != planned_module.get("required"):
            raise RuntimeError(f"module execution module {module_id} changed its required binding")
        if str(module.get("execution_mode") or "") != str(planned_module.get("execution_mode") or ""):
            raise RuntimeError(f"module execution module {module_id} changed its execution_mode binding")
        if module.get("gap_reason") != planned_module.get("gap_reason"):
            raise RuntimeError(f"module execution module {module_id} changed its gap_reason binding")
        if str(module.get("state") or "") not in {
            "completed",
            "failed",
            "blocked",
        }:
            raise RuntimeError(f"module execution module {module_id} is not terminal")

        planned_criteria = [
            criterion
            for criterion in planned_module.get("acceptance_criteria") or []
            if isinstance(criterion, dict) and str(criterion.get("criterion_id") or "")
        ]
        criterion_results = module.get("criterion_results")
        if not isinstance(criterion_results, list) or any(
            not isinstance(result, dict) for result in criterion_results
        ):
            raise RuntimeError(
                f"module execution module {module_id} criterion_results must be a JSON array of objects"
            )
        planned_criterion_ids = [str(criterion["criterion_id"]) for criterion in planned_criteria]
        submitted_criterion_ids = [
            str(result.get("criterion_id") or "") for result in criterion_results
        ]
        if (
            set(submitted_criterion_ids) != set(planned_criterion_ids)
            or len(submitted_criterion_ids) != len(planned_criterion_ids)
        ):
            raise RuntimeError(
                f"module execution module {module_id} criterion results must exactly match the approved plan"
            )
        for result in criterion_results:
            criterion_id = str(result.get("criterion_id") or "")
            if "state" not in result:
                raise RuntimeError(
                    f"module execution criterion {module_id}:{criterion_id} is missing required field: state"
                )
            criterion_state = str(result.get("state") or "")
            if criterion_state not in {"passing", "failing", "blocked"}:
                raise RuntimeError(
                    f"module execution criterion {module_id}:{criterion_id} has unsupported state: {criterion_state}"
                )


def _mark_host_launch_failed(receipt_path: Path, receipt: HostLaunchReceipt) -> None:
    failed_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "failed"})
    write_host_launch_receipt(receipt_path, failed_receipt)


def _finalize_canonical_launch_result(
    *,
    receipt: HostLaunchReceipt,
    receipt_path: Path,
    requested_entry_id: str,
    requested_stage_stop: str | None,
    effective_requested_stage_stop: str | None,
    effective_prompt: str,
    payload: dict[str, Any],
    fallback_run_id: str,
    fallback_summary_path: Path,
) -> CanonicalLaunchResult:
    session_root = Path(str(payload["session_root"])).resolve()
    resolved_run_id = str(payload.get("run_id") or fallback_run_id or session_root.name)
    summary_path = Path(str(payload.get("summary_path") or fallback_summary_path)).resolve()

    summary = dict(payload.get("summary") or {})
    if summary_path.exists():
        summary = _load_json_dict(summary_path, label="runtime-summary")

    if receipt_path.parent != session_root:
        receipt_path = write_host_launch_receipt(session_root, receipt)

    artifacts = assert_minimum_truth_artifacts(session_root)
    _ = _load_runtime_truth_packet(Path(artifacts["runtime_input_packet"]))
    assert_minimum_truth_consistency(
        receipt=receipt,
        runtime_packet_path=artifacts["runtime_input_packet"],
        governance_capsule_path=artifacts["governance_capsule"],
        stage_lineage_path=artifacts["stage_lineage"],
    )

    stage_lineage = _load_json_dict(Path(artifacts["stage_lineage"]), label="stage-lineage")
    runtime_packet = _load_json_dict(Path(artifacts["runtime_input_packet"]), label="runtime-input-packet")
    terminal_stage = _resolve_canonical_terminal_stage(
        stage_lineage_payload=stage_lineage,
        summary=summary,
        effective_requested_stage_stop=effective_requested_stage_stop,
    )
    module_execution_path = _artifact_path_from_artifacts(
        dict(summary.get("artifacts") or {}),
        "module_execution",
        base_dir=summary_path.parent,
    )
    module_execution = (
        _load_json_dict(module_execution_path, label="module-execution")
        if module_execution_path and module_execution_path.is_file()
        else None
    )
    summary = build_runtime_summary(
        run_id=resolved_run_id,
        task=effective_prompt,
        artifacts=dict(summary.get("artifacts") or {}),
        module_assignments=runtime_packet["module_assignments"],
        module_execution=module_execution,
        base_fields={
            **summary,
            "requested_stage_stop": requested_stage_stop,
            "effective_requested_stage_stop": effective_requested_stage_stop,
            "stage_stop_source": _resolve_canonical_stage_stop_source(
                requested_stage_stop=requested_stage_stop,
                effective_requested_stage_stop=effective_requested_stage_stop,
            ),
            "terminal_stage": terminal_stage,
        },
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    verified_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "verified"})
    receipt_path = write_host_launch_receipt(receipt_path, verified_receipt)

    artifacts["host_launch_receipt"] = str(receipt_path)
    return CanonicalLaunchResult(
        run_id=resolved_run_id,
        session_root=session_root,
        summary_path=summary_path,
        host_launch_receipt_path=receipt_path,
        launch_mode=verified_receipt.launch_mode,
        summary=summary,
        artifacts=artifacts,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for launching canonical vibe and emitting JSON output."""
    argv = list(argv or sys.argv[1:])
    if "--build-runtime-truth-input-json" in argv:
        parser = argparse.ArgumentParser(
            description="Build a Python-owned runtime truth packet from a staged payload."
        )
        parser.add_argument("--build-runtime-truth-input-json", required=True)
        parser.add_argument("--output-json-path", required=True)
        args = parser.parse_args(argv)
        build_runtime_truth_payload(
            input_json_path=args.build_runtime_truth_input_json,
            output_json_path=args.output_json_path,
        )
        return 0

    if "--finalize-runtime-summary-input-json" in argv:
        parser = argparse.ArgumentParser(
            description="Finalize a Python-owned runtime summary from a staged payload."
        )
        parser.add_argument("--finalize-runtime-summary-input-json", required=True)
        parser.add_argument("--output-json-path", required=True)
        args = parser.parse_args(argv)
        finalize_runtime_summary_payload(
            input_json_path=args.finalize_runtime_summary_input_json,
            output_json_path=args.output_json_path,
        )
        return 0

    if "--refresh-runtime-summary-acceptance" in argv:
        parser = argparse.ArgumentParser(
            description="Refresh a Python-owned runtime summary from final delivery acceptance."
        )
        parser.add_argument("--refresh-runtime-summary-acceptance", action="store_true")
        parser.add_argument("--runtime-summary-json", required=True)
        parser.add_argument("--delivery-acceptance-report-json", required=True)
        parser.add_argument("--cleanup-receipt-path", required=True)
        args = parser.parse_args(argv)
        refresh_runtime_summary_acceptance_payload(
            summary_json_path=args.runtime_summary_json,
            delivery_acceptance_report_json_path=args.delivery_acceptance_report_json,
            cleanup_receipt_path=args.cleanup_receipt_path,
        )
        return 0

    parser = argparse.ArgumentParser(description="Launch canonical vibe entry and emit receipt-backed JSON output.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--host-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--entry-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--requested-stage-stop")
    parser.add_argument("--requested-grade-floor", choices=("L", "XL"))
    parser.add_argument("--run-id")
    parser.add_argument("--workspace-root", help=argparse.SUPPRESS)
    parser.add_argument("--artifact-root")
    parser.add_argument("--local-agent-root")
    parser.add_argument("--continue-from-run-id")
    parser.add_argument("--bounded-reentry-token")
    parser.add_argument("--module-execution-json-file")
    parser.add_argument("--host-decision-json")
    parser.add_argument("--host-decision-json-file")
    parser.add_argument("--force-runtime-neutral", action="store_true")
    args = parser.parse_args(argv)
    host_decision = _parse_host_decision_json(args.host_decision_json, args.host_decision_json_file)

    try:
        result = launch_canonical_vibe(
            repo_root=args.repo_root,
            host_id=args.host_id,
            entry_id=args.entry_id,
            prompt=args.prompt,
            requested_stage_stop=args.requested_stage_stop,
            requested_grade_floor=args.requested_grade_floor,
            run_id=args.run_id,
            workspace_root=args.workspace_root,
            artifact_root=args.artifact_root,
            local_agent_root=args.local_agent_root,
            continue_from_run_id=args.continue_from_run_id,
            bounded_reentry_token=args.bounded_reentry_token,
            module_execution_json_file=args.module_execution_json_file,
            host_decision=host_decision,
            force_runtime_neutral=bool(args.force_runtime_neutral),
        )
    except EntryRootGuardError as exc:
        raise SystemExit(str(exc)) from None
    output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    stdout_buffer = getattr(sys.stdout, "buffer", None)
    if stdout_buffer is not None:
        stdout_buffer.write(output.encode("utf-8"))
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
