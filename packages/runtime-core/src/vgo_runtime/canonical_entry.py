from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
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
from vgo_contracts.host_launch_receipt import HostLaunchReceipt, write_host_launch_receipt
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


def _load_json_dict_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_prompt_token(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    lowered = lowered.strip("-")
    if len(lowered) > 64:
        lowered = lowered[:64].rstrip("-")
    return lowered


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


def _should_apply_continuation(entry_id: str, prompt_text: str) -> bool:
    if entry_id not in {"vibe-how", "vibe-do"}:
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
    entry_id: str,
    run_id: str | None,
    preferred_run_id: str | None = None,
    allow_bounded_preferred: bool = False,
) -> dict[str, Any] | None:
    required_artifact = "requirement_doc" if entry_id == "vibe-how" else "execution_plan"
    preferred = str(preferred_run_id or "").strip()
    if preferred:
        preferred_summary = _continuation_sessions_root(artifact_root) / preferred / "runtime-summary.json"
        if preferred_summary.is_file():
            preferred_summary_payload = _load_json_dict_if_exists(preferred_summary)
            if not (preferred_summary_payload and _coerce_bounded_return_control(preferred_summary_payload) and not allow_bounded_preferred):
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
        if _coerce_bounded_return_control(summary):
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
    artifacts = summary.get("artifacts") or {}
    required_path = artifacts.get(required_artifact)
    intent_contract_path = artifacts.get("intent_contract")
    if not required_path or not Path(required_path).exists():
        return None
    intent_contract = _load_json_dict_if_exists(Path(intent_contract_path)) if intent_contract_path else None
    if not intent_contract:
        return None
    return {
        "summary_path": str(summary_path),
        "run_id": str(summary.get("run_id") or summary_path.parent.name),
        "terminal_stage": str(summary.get("terminal_stage") or ""),
        "required_artifact": str(required_path),
        "intent_contract": intent_contract,
    }


def _resolve_effective_prompt(
    *,
    host_id: str,
    entry_id: str,
    prompt: str,
    artifact_root: Path | None = None,
    run_id: str | None = None,
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

    if artifact_root is not None and _should_apply_continuation(entry_id, prompt_text):
        continuation = _find_continuation_context(
            artifact_root=artifact_root,
            entry_id=entry_id,
            run_id=run_id,
            preferred_run_id=continuation_source_run_id,
            allow_bounded_preferred=allow_bounded_preferred_source,
        )
        if continuation:
            return _build_continuation_prompt(prompt_text=prompt_text, entry_id=entry_id, continuation=continuation)

    return prompt_text


def _coerce_bounded_return_control(summary: dict[str, Any]) -> dict[str, Any] | None:
    raw = summary.get("bounded_return_control")
    if not isinstance(raw, dict):
        return None
    if not bool(raw.get("explicit_user_reentry_required")):
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

    artifacts = summary.get("artifacts") or {}
    intent_contract = _load_json_dict_if_exists(Path(artifacts["intent_contract"])) if artifacts.get("intent_contract") else None
    return {
        "summary_path": str(summary.get("summary_path") or ""),
        "source_run_id": source_run_id,
        "terminal_stage": terminal_stage,
        "allowed_followup_entry_ids": allowed_followup,
        "reentry_token": token,
        "task": str(summary.get("task") or ""),
        "intent_goal": str(intent_contract.get("goal") or "") if intent_contract else "",
    }


def _find_latest_bounded_return_control(
    *,
    artifact_root: Path,
    run_id: str | None,
    preferred_run_id: str | None = None,
) -> dict[str, Any] | None:
    preferred = str(preferred_run_id or "").strip()
    if preferred:
        preferred_summary_path = _continuation_sessions_root(artifact_root) / preferred / "runtime-summary.json"
        preferred_summary = _load_json_dict_if_exists(preferred_summary_path)
        if preferred_summary:
            preferred_guard = _coerce_bounded_return_control(preferred_summary)
            if preferred_guard:
                preferred_guard["summary_path"] = str(preferred_summary_path)
                return preferred_guard

    for summary_path in _iter_runtime_summaries(artifact_root):
        if run_id and summary_path.parent.name == run_id:
            continue
        summary = _load_json_dict_if_exists(summary_path)
        if not summary:
            continue
        guard = _coerce_bounded_return_control(summary)
        if guard:
            guard["summary_path"] = str(summary_path)
            return guard
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


def _validate_bounded_reentry(
    *,
    artifact_root: Path | None,
    entry_id: str,
    prompt: str,
    run_id: str | None,
    continue_from_run_id: str | None,
    bounded_reentry_token: str | None,
) -> dict[str, Any] | None:
    if artifact_root is None:
        return None

    prior_guard = _find_latest_bounded_return_control(
        artifact_root=artifact_root,
        run_id=run_id,
        preferred_run_id=continue_from_run_id,
    )
    if not prior_guard:
        return None
    if entry_id not in set(prior_guard["allowed_followup_entry_ids"]):
        return None
    if not _looks_like_generic_reentry_prompt(prompt, entry_id=entry_id, bounded_return_control=prior_guard):
        return None

    provided_run_id = str(continue_from_run_id or "").strip()
    provided_token = str(bounded_reentry_token or "").strip()
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
    if router_requested_skill and router_requested_skill != requested_entry_id:
        raise RuntimeError("requested entry mismatch between canonical request and canonical_router")

    route_snapshot = runtime_packet.get("route_snapshot")
    if not isinstance(route_snapshot, dict):
        raise RuntimeError("canonical truth packet missing route_snapshot object")
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
    if receipt.requested_stage_stop and terminal_stage != receipt.requested_stage_stop:
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
    force_runtime_neutral: bool = False,
) -> CanonicalLaunchResult:
    """Launch canonical vibe, verify its artifacts, and return launch metadata."""
    repo_root_path = Path(repo_root).resolve()
    requested_entry_id = _normalize_requested_entry_id(entry_id)
    resolved_artifact_root = _resolve_artifact_root(repo_root_path, artifact_root)
    validated_reentry = _validate_bounded_reentry(
        artifact_root=resolved_artifact_root,
        entry_id=requested_entry_id,
        prompt=prompt,
        run_id=run_id,
        continue_from_run_id=continue_from_run_id,
        bounded_reentry_token=bounded_reentry_token,
    )
    effective_prompt = _resolve_effective_prompt(
        host_id=host_id,
        entry_id=requested_entry_id,
        prompt=prompt,
        artifact_root=resolved_artifact_root,
        run_id=run_id,
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
        requested_stage_stop=requested_stage_stop,
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
            requested_stage_stop=requested_stage_stop,
            requested_grade_floor=requested_grade_floor,
            run_id=resolved_run_id,
            artifact_root=resolved_artifact_root,
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
    parser.add_argument("--force-runtime-neutral", action="store_true")
    args = parser.parse_args(argv)

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
        force_runtime_neutral=bool(args.force_runtime_neutral),
    )
    json.dump(result.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0
