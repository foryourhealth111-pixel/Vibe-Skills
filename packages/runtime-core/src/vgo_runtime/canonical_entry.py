from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys
from typing import Any
import warnings

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
POWERSHELL_HOST_POLICY_PATH = REPO_ROOT / "config" / "powershell-host-policy.json"
POWERSHELL_HOST_POLICY_DEFAULTS: dict[str, Any] = {
    "preferred_powershell_host": "pwsh",
    "require_pwsh_on_non_windows": True,
    "allow_windows_powershell_fallback": True,
    "record_host_resolution_artifacts": True,
}
SUPPORTED_POWERSHELL_HOSTS = frozenset({"pwsh", "windows-powershell"})
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.canonical_vibe_contract import resolve_canonical_vibe_contract
from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface
from vgo_contracts.host_launch_receipt import HostLaunchReceipt, read_host_launch_receipt, write_host_launch_receipt
from vgo_runtime.powershell_bridge import run_powershell_json_command
from vgo_runtime.router import load_allowed_vibe_entry_ids

RUNTIME_ENTRYPOINT_RELPATH = "scripts/runtime/invoke-vibe-runtime.ps1"
CANONICAL_ENTRY_BRIDGE_RELPATH = "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"
CANONICAL_RUNTIME_ENTRY_ID = "vibe"
MINIMUM_TRUTH_ARTIFACTS = {
    "runtime_input_packet": "runtime-input-packet.json",
    "governance_capsule": "governance-capsule.json",
    "stage_lineage": "stage-lineage.json",
}
REQUIRED_TRUTH_PACKET_FIELDS = (
    "canonical_router",
    "route_snapshot",
    "specialist_recommendations",
    "specialist_dispatch",
    "divergence_shadow",
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
    """Normalize and validate the requested canonical entry identifier."""
    requested_entry_id = str(entry_id or "").strip() or CANONICAL_RUNTIME_ENTRY_ID
    if requested_entry_id not in load_allowed_vibe_entry_ids():
        raise RuntimeError(f"unsupported canonical vibe entry id: {requested_entry_id}")
    return requested_entry_id


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


def _load_intent_contract_from_artifacts(artifacts: dict[str, Any]) -> dict[str, Any] | None:
    intent_contract_path = _artifact_path_value(artifacts, "intent_contract")
    if not intent_contract_path:
        return None
    return _load_json_dict_if_exists(Path(intent_contract_path))


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

    if effective_decision.get("phase_decomposition") is None:
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
        and effective_decision.get("specialist_dispatch_decision") is None
    ):
        prior_specialist_dispatch_decision = runtime_packet.get("host_specialist_dispatch_decision")
        if isinstance(prior_specialist_dispatch_decision, dict):
            effective_decision["specialist_dispatch_decision"] = copy.deepcopy(
                prior_specialist_dispatch_decision
            )

    return effective_decision or None


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


def _parse_host_decision_json(host_decision_json: str | None) -> dict[str, Any] | None:
    raw = str(host_decision_json or "").strip()
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
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


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

    deliverable = str(continuation.get("intent_deliverable") or "").strip()
    if deliverable and deliverable.lower() != "unknown":
        segments.append(f"Deliverable: {deliverable}.")

    constraints = _normalize_text_list(continuation.get("intent_constraints"))
    if constraints:
        segments.append(f"Constraints: {'; '.join(constraints)}.")

    delta = str(prompt_text or "").strip()
    if delta and not _is_control_only_structured_reentry_prompt(delta):
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

    enriched = copy.deepcopy(decision)
    enriched["continuation_context"] = {
        "structured_bounded_reentry": True,
        "source_run_id": str(bounded_reentry.get("source_run_id") or "").strip() or None,
        "terminal_stage": str(bounded_reentry.get("terminal_stage") or "").strip() or None,
        "next_stage": str(bounded_reentry.get("next_stage") or "").strip() or None,
        "prior_task": str(bounded_reentry.get("task") or "").strip() or None,
        "prior_task_type": str(bounded_reentry.get("prior_task_type") or "").strip() or None,
        "prior_goal": str(bounded_reentry.get("intent_goal") or "").strip() or None,
        "prior_deliverable": str(bounded_reentry.get("intent_deliverable") or "").strip() or None,
        "prior_constraints": _normalize_text_list(bounded_reentry.get("intent_constraints")),
        "control_only_prompt": _is_control_only_structured_reentry_prompt(prompt_text),
    }
    return enriched


def _progressive_stage_stops(repo_root: Path, entry_id: str) -> tuple[str, ...]:
    candidates: list[Path] = [repo_root]
    resolved_repo_root = repo_root.resolve()
    if resolved_repo_root != REPO_ROOT.resolve():
        candidates.append(REPO_ROOT)

    for candidate in candidates:
        try:
            surface = load_discoverable_entry_surface(candidate)
        except RuntimeError:
            continue
        entry = surface.entry_by_id.get(entry_id)
        if entry is not None:
            return tuple(entry.progressive_stage_stops)
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
            terminal_index = progressive_stage_stops.index(terminal_stage)
            if terminal_index + 1 < len(progressive_stage_stops):
                return progressive_stage_stops[terminal_index + 1]
            return terminal_stage

    return progressive_stage_stops[0]


def _required_continuation_artifact(
    *,
    entry_id: str,
    bounded_reentry: dict[str, Any] | None,
) -> str | None:
    if entry_id == "vibe-how-do-we-do":
        return "requirement_doc"
    if entry_id == "vibe-do-it":
        return "execution_plan"
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
    if entry_id not in {"vibe-how-do-we-do", "vibe-do-it"}:
        return False
    normalized = prompt_text.strip().lower()
    if not normalized:
        return False
    if len(normalized.split()) <= 24:
        return True
    return normalized.startswith("execute ") or normalized.startswith("plan ")


def _find_continuation_context(
    *,
    artifact_root: Path,
    required_artifact: str,
    run_id: str | None,
    preferred_run_id: str | None = None,
    allow_bounded_preferred: bool = False,
) -> dict[str, Any] | None:
    preferred_summary = _runtime_summary_path_for_run_id(artifact_root, preferred_run_id)
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
    required_path = _artifact_path_value(artifacts, required_artifact)
    if not required_path or not Path(required_path).exists():
        return None
    intent_contract = _load_intent_contract_from_artifacts(artifacts)
    if not intent_contract:
        return None
    runtime_packet = _load_runtime_input_packet_from_summary(summary_path)
    prior_task_type = ""
    if isinstance(runtime_packet, dict):
        canonical_router = runtime_packet.get("canonical_router")
        if isinstance(canonical_router, dict):
            prior_task_type = str(canonical_router.get("task_type") or "").strip()
    return {
        "summary_path": str(summary_path),
        "run_id": str(summary.get("run_id") or summary_path.parent.name),
        "terminal_stage": str(summary.get("terminal_stage") or ""),
        "required_artifact": str(required_path),
        "task": str(summary.get("task") or ""),
        "prior_task_type": prior_task_type,
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
    """Derive the runtime prompt, including upgrade fallback and continuation context."""
    prompt_text = str(prompt or "")
    if not prompt_text.strip() and entry_id == "vibe-upgrade":
        resolved_host_id = str(host_id or "").strip() or "current-host"
        return (
            f"Upgrade the local Vibe-Skills installation for host {resolved_host_id} "
            "using the shared vgo-cli upgrade flow against the official default branch. "
            "Reinstall the supported host surface, verify the result, and report concise before-and-after status."
        )

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
                return _build_structured_continuation_prompt(
                    prompt_text=prompt_text,
                    continuation=continuation,
                )
            return _build_continuation_prompt(prompt_text=prompt_text, entry_id=entry_id, continuation=continuation)

    return prompt_text


def _coerce_bounded_return_control(summary: dict[str, Any]) -> dict[str, Any] | None:
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
    intent_contract = _load_intent_contract_from_artifacts(artifacts)
    runtime_packet_path = _artifact_path_value(artifacts, "runtime_input_packet")
    runtime_packet = _load_json_dict_if_exists(Path(runtime_packet_path)) if runtime_packet_path else {}
    prior_task_type = ""
    if isinstance(runtime_packet, dict):
        canonical_router = runtime_packet.get("canonical_router")
        if isinstance(canonical_router, dict):
            prior_task_type = str(canonical_router.get("task_type") or "").strip()
    return {
        "summary_path": str(summary.get("summary_path") or ""),
        "source_run_id": source_run_id,
        "terminal_stage": terminal_stage,
        "next_stage": str(raw.get("next_stage") or "").strip(),
        "allowed_followup_entry_ids": allowed_followup,
        "reentry_token": token,
        "task": str(summary.get("task") or ""),
        "intent_goal": str(intent_contract.get("goal") or "") if intent_contract else "",
        "intent_deliverable": str(intent_contract.get("deliverable") or "") if intent_contract else "",
        "intent_constraints": _normalize_text_list(intent_contract.get("constraints")) if intent_contract else [],
        "prior_task_type": prior_task_type,
    }


def _has_explicit_bounded_return_control(summary: dict[str, Any]) -> bool:
    raw = summary.get("bounded_return_control")
    return isinstance(raw, dict) and bool(raw.get("explicit_user_reentry_required"))


def _build_malformed_bounded_return_control(summary: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    artifacts = _artifact_paths(summary)
    intent_contract = _load_intent_contract_from_artifacts(artifacts)
    runtime_packet_path = _artifact_path_value(artifacts, "runtime_input_packet")
    runtime_packet = _load_json_dict_if_exists(Path(runtime_packet_path)) if runtime_packet_path else {}
    prior_task_type = ""
    if isinstance(runtime_packet, dict):
        canonical_router = runtime_packet.get("canonical_router")
        if isinstance(canonical_router, dict):
            prior_task_type = str(canonical_router.get("task_type") or "").strip()
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
        "prior_task_type": prior_task_type,
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
            preferred_guard = _coerce_bounded_return_control(preferred_summary)
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
        guard = _coerce_bounded_return_control(summary)
        if guard:
            guard["summary_path"] = str(summary_path)
            return guard
        return _build_malformed_bounded_return_control(summary, summary_path)
    return None


def _looks_like_generic_reentry_prompt(
    prompt_text: str,
    *,
    entry_id: str,
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
    decision = _normalize_host_decision(host_decision)
    if not decision:
        return False

    terminal_stage = str(bounded_return_control.get("terminal_stage") or "").strip()
    if not terminal_stage:
        return False

    allowed_actions = STRUCTURED_REENTRY_APPROVAL_ACTIONS.get(terminal_stage)
    if not allowed_actions:
        return False

    decision_kind = str(decision.get("decision_kind") or "").strip().lower()
    decision_action = str(decision.get("decision_action") or "").strip().lower()
    approval_decision = str(decision.get("approval_decision") or "").strip().lower()

    if approval_decision == "approve":
        return True
    if decision_action in allowed_actions:
        return True
    if decision_kind == "approval_response" and decision_action == "approve":
        return True
    return False


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
    fallback_prompt_reentry = _looks_like_generic_reentry_prompt(prompt, entry_id=entry_id, bounded_return_control=prior_guard)
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
    structured_reentry = _structured_host_decision_allows_bounded_reentry(
        host_decision,
        bounded_return_control=prior_guard,
    )
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
                    f"{expected_stage}; send an explicit approval decision for the pending governed stop"
                )
            raise RuntimeError(
                "prompt does not look like a bounded-wrapper continuation for "
                f"{expected_stage}; provide a continuation prompt or remove the explicit re-entry credentials"
            )
        return None

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
    return prior_guard


def _new_run_id() -> str:
    """Generate a unique canonical launch run identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = os.urandom(4).hex()
    return f"{timestamp}-{suffix}"


def _resolve_artifact_root(repo_root: Path, artifact_root: str | Path | None) -> Path:
    """Resolve the artifact root relative to the repository when needed."""
    if artifact_root in (None, ""):
        return (repo_root / ".vibeskills").resolve()

    artifact_root_path = Path(str(artifact_root)).expanduser()
    if artifact_root_path.is_absolute():
        return artifact_root_path.resolve()
    return (repo_root / artifact_root_path).resolve()


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
    artifact_root: str | Path | None,
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
    if artifact_root:
        command.extend(["-ArtifactRoot", str(Path(artifact_root))])
    serialized_host_decision = _serialize_host_decision_json(host_decision)
    if serialized_host_decision:
        command.extend(["-HostDecisionJson", serialized_host_decision])

    env = dict(os.environ)
    env["VCO_HOST_ID"] = host_id
    return run_powershell_json_command(
        command,
        cwd=repo_root,
        bridge_label="canonical entry bridge",
        env=env,
    )


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


def _extract_terminal_stage(stage_lineage: dict[str, Any]) -> str | None:
    """Extract the terminal stage name from known stage-lineage shapes."""
    last_stage_name = str(stage_lineage.get("last_stage_name") or stage_lineage.get("last_stage") or "").strip()
    if last_stage_name:
        return last_stage_name
    stages = stage_lineage.get("stages")
    if isinstance(stages, list) and stages:
        tail = stages[-1]
        if isinstance(tail, dict):
            stage_name = str(tail.get("stage_name") or tail.get("stage") or "").strip()
            if stage_name:
                return stage_name
    entries = stage_lineage.get("entries")
    if isinstance(entries, list) and entries:
        tail = entries[-1]
        if isinstance(tail, dict):
            stage_name = str(tail.get("stage_name") or tail.get("stage") or "").strip()
            if stage_name:
                return stage_name
    stage_name = str(stage_lineage.get("stage_name") or stage_lineage.get("stage") or "").strip()
    return stage_name or None


def assert_minimum_truth_consistency(
    *,
    receipt: HostLaunchReceipt,
    requested_entry_id: str,
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

    packet_host_id = str(runtime_packet.get("host_id") or "").strip()
    if packet_host_id and packet_host_id != receipt.host_id:
        raise RuntimeError("host_id mismatch between host launch receipt and runtime packet")

    packet_entry_intent_id = str(runtime_packet.get("entry_intent_id") or "").strip()
    if packet_entry_intent_id and packet_entry_intent_id != requested_entry_id:
        raise RuntimeError("entry_intent_id mismatch between canonical request and runtime packet")

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
    if not isinstance(canonical_router, dict):
        raise RuntimeError("canonical truth packet missing canonical_router object")
    router_host_id = str(canonical_router.get("host_id") or "").strip()
    if not router_host_id:
        raise RuntimeError("canonical truth packet missing canonical_router host_id")
    if router_host_id != receipt.host_id:
        raise RuntimeError("host_id mismatch between host launch receipt and canonical_router")
    router_requested_skill = str(canonical_router.get("requested_skill") or "").strip()
    if router_requested_skill and router_requested_skill != CANONICAL_RUNTIME_ENTRY_ID:
        raise RuntimeError("canonical_router requested_skill must remain canonical vibe or be omitted")

    route_snapshot = runtime_packet.get("route_snapshot")
    if not isinstance(route_snapshot, dict):
        raise RuntimeError("canonical truth packet missing route_snapshot object")
    confirm_required = bool(route_snapshot.get("confirm_required"))
    selected_skill = str(route_snapshot.get("selected_skill") or "").strip()
    if not selected_skill:
        raise RuntimeError("canonical truth packet missing route_snapshot selected_skill")

    specialist_recommendations = runtime_packet.get("specialist_recommendations")
    if not isinstance(specialist_recommendations, list) or not specialist_recommendations:
        raise RuntimeError("canonical truth packet must preserve specialist recommendation evidence")

    specialist_dispatch = runtime_packet.get("specialist_dispatch")
    if not isinstance(specialist_dispatch, dict):
        raise RuntimeError("canonical truth packet missing specialist_dispatch object")
    for dispatch_key in ("approved_dispatch", "local_specialist_suggestions"):
        if dispatch_key not in specialist_dispatch:
            raise RuntimeError(f"canonical truth packet missing specialist_dispatch.{dispatch_key}")

    governance_capsule = _load_json_dict(Path(governance_capsule_path), label="governance-capsule")
    runtime_selected_skill = str(governance_capsule.get("runtime_selected_skill") or "").strip()
    if runtime_selected_skill != CANONICAL_RUNTIME_ENTRY_ID:
        raise RuntimeError("governance capsule must keep vibe as runtime authority")

    divergence_shadow = runtime_packet.get("divergence_shadow")
    if not isinstance(divergence_shadow, dict):
        raise RuntimeError("canonical truth packet missing divergence_shadow object")
    divergence_runtime_skill = str(divergence_shadow.get("runtime_selected_skill") or "").strip()
    if divergence_runtime_skill != CANONICAL_RUNTIME_ENTRY_ID:
        raise RuntimeError("divergence_shadow must keep vibe as runtime authority")
    divergence_router_skill = str(divergence_shadow.get("router_selected_skill") or "").strip()
    if not divergence_router_skill:
        raise RuntimeError("canonical truth packet missing divergence_shadow router_selected_skill")
    if divergence_router_skill != selected_skill:
        raise RuntimeError("route_snapshot selected_skill mismatch with divergence_shadow")

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
        if confirm_required:
            if terminal_stage != "skeleton_check":
                raise RuntimeError("confirm-required runtime stop must return before governed stage progression")
        elif terminal_stage != receipt.requested_stage_stop:
            raise RuntimeError("bounded stop mismatch between host launch receipt and stage-lineage")


def launch_canonical_vibe(
    *,
    repo_root: str | Path,
    host_id: str,
    entry_id: str,
    prompt: str,
    requested_stage_stop: str | None = None,
    requested_grade_floor: str | None = None,
    run_id: str | None = None,
    artifact_root: str | Path | None = None,
    continue_from_run_id: str | None = None,
    bounded_reentry_token: str | None = None,
    host_decision: dict[str, Any] | None = None,
    force_runtime_neutral: bool = False,
) -> CanonicalLaunchResult:
    """Launch canonical vibe, verify its artifacts, and return launch metadata."""
    repo_root_path = Path(repo_root).resolve()
    requested_entry_id = _normalize_requested_entry_id(entry_id)
    resolved_artifact_root = _resolve_artifact_root(repo_root_path, artifact_root)
    normalized_host_decision = _normalize_host_decision(host_decision)
    validated_reentry = _validate_bounded_reentry(
        artifact_root=resolved_artifact_root,
        entry_id=requested_entry_id,
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
        requested_stage_stop=requested_stage_stop,
        bounded_reentry=validated_reentry,
    )
    effective_prompt = _resolve_effective_prompt(
        host_id=host_id,
        entry_id=requested_entry_id,
        prompt=prompt,
        host_decision=effective_host_decision,
        artifact_root=resolved_artifact_root,
        run_id=run_id,
        bounded_reentry=validated_reentry,
        continuation_source_run_id=(str(validated_reentry["source_run_id"]) if validated_reentry else None),
        allow_bounded_preferred_source=bool(validated_reentry),
    )
    contract = resolve_canonical_vibe_contract(repo_root_path, host_id)
    if str(contract.get("fallback_policy") or "").strip() != "blocked":
        raise RuntimeError("unsupported fallback policy for canonical entry launcher")
    if bool(contract.get("allow_skill_doc_fallback", False)):
        raise RuntimeError("unsupported fallback policy for canonical entry launcher")

    resolved_run_id = str(run_id or "").strip() or _new_run_id()
    session_root = _resolve_session_root(repo_root=repo_root_path, run_id=resolved_run_id, artifact_root=artifact_root)
    summary_path = (session_root / "runtime-summary.json").resolve()
    receipt = HostLaunchReceipt(
        host_id=host_id,
        entry_id=CANONICAL_RUNTIME_ENTRY_ID,
        launch_mode="canonical-entry",
        launcher_path=str((repo_root_path / CANONICAL_ENTRY_BRIDGE_RELPATH).resolve()),
        requested_stage_stop=effective_requested_stage_stop,
        requested_grade_floor=requested_grade_floor,
        runtime_entrypoint=str((repo_root_path / RUNTIME_ENTRYPOINT_RELPATH).resolve()),
        run_id=resolved_run_id,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        launch_status="launched",
    )
    receipt_path = write_host_launch_receipt(session_root, receipt)

    try:
        payload = invoke_vibe_runtime_entrypoint(
            repo_root=repo_root_path,
            host_id=host_id,
            entry_id=requested_entry_id,
            prompt=effective_prompt,
            requested_stage_stop=effective_requested_stage_stop,
            requested_grade_floor=requested_grade_floor,
            run_id=resolved_run_id,
            artifact_root=resolved_artifact_root,
            host_decision=effective_host_decision,
            force_runtime_neutral=force_runtime_neutral,
        )
    except Exception:
        failed_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "failed"})
        write_host_launch_receipt(receipt_path, failed_receipt)
        raise

    session_root = Path(str(payload["session_root"])).resolve()
    resolved_run_id = str(payload.get("run_id") or resolved_run_id or session_root.name)
    summary_path = Path(str(payload.get("summary_path") or summary_path)).resolve()

    summary = dict(payload.get("summary") or {})
    if summary_path.exists():
        summary = _load_json_dict(summary_path, label="runtime-summary")

    if receipt_path.parent != session_root:
        receipt_path = write_host_launch_receipt(session_root, receipt)

    try:
        artifacts = assert_minimum_truth_artifacts(session_root)
        assert_minimum_truth_consistency(
            receipt=receipt,
            requested_entry_id=requested_entry_id,
            runtime_packet_path=artifacts["runtime_input_packet"],
            governance_capsule_path=artifacts["governance_capsule"],
            stage_lineage_path=artifacts["stage_lineage"],
        )
    except Exception:
        failed_receipt = HostLaunchReceipt(**{**receipt.model_dump(), "launch_status": "failed"})
        write_host_launch_receipt(receipt_path, failed_receipt)
        raise

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
    parser = argparse.ArgumentParser(description="Launch canonical vibe entry and emit receipt-backed JSON output.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--host-id", default="codex")
    parser.add_argument("--entry-id", default="vibe")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--requested-stage-stop")
    parser.add_argument("--requested-grade-floor", choices=("L", "XL"))
    parser.add_argument("--run-id")
    parser.add_argument("--artifact-root")
    parser.add_argument("--continue-from-run-id")
    parser.add_argument("--bounded-reentry-token")
    parser.add_argument("--host-decision-json")
    parser.add_argument("--force-runtime-neutral", action="store_true")
    args = parser.parse_args(argv)
    host_decision = _parse_host_decision_json(args.host_decision_json)

    result = launch_canonical_vibe(
        repo_root=args.repo_root,
        host_id=args.host_id,
        entry_id=args.entry_id,
        prompt=args.prompt,
        requested_stage_stop=args.requested_stage_stop,
        requested_grade_floor=args.requested_grade_floor,
        run_id=args.run_id,
        artifact_root=args.artifact_root,
        continue_from_run_id=args.continue_from_run_id,
        bounded_reentry_token=args.bounded_reentry_token,
        host_decision=host_decision,
        force_runtime_neutral=bool(args.force_runtime_neutral),
    )
    json.dump(result.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0
