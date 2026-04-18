from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

CONTRACTS_SRC = Path(__file__).resolve().parents[4] / "packages" / "contracts" / "src"
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.canonical_vibe_contract import resolve_canonical_vibe_contract
from vgo_contracts.host_launch_receipt import HostLaunchReceipt, write_host_launch_receipt
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
    run_id: str
    session_root: Path
    summary_path: Path
    host_launch_receipt_path: Path
    launch_mode: str
    summary: dict[str, Any]
    artifacts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["session_root"] = str(self.session_root)
        payload["summary_path"] = str(self.summary_path)
        payload["host_launch_receipt_path"] = str(self.host_launch_receipt_path)
        payload["artifacts"] = dict(self.artifacts)
        return payload


# Backward-compatible alias for callers that imported the scaffold name.
CanonicalEntryResult = CanonicalLaunchResult


def _resolve_powershell_host() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def _load_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object JSON in {label}: {path}")
    return payload


def _normalize_requested_entry_id(entry_id: str | None) -> str:
    requested_entry_id = str(entry_id or "").strip() or CANONICAL_RUNTIME_ENTRY_ID
    if requested_entry_id not in load_allowed_vibe_entry_ids():
        raise RuntimeError(f"unsupported canonical vibe entry id: {requested_entry_id}")
    return requested_entry_id


def _resolve_effective_prompt(*, host_id: str, entry_id: str, prompt: str) -> str:
    prompt_text = str(prompt or "")
    if prompt_text.strip():
        return prompt_text
    if entry_id != "vibe-upgrade":
        return prompt_text
    resolved_host_id = str(host_id or "").strip() or "current-host"
    return (
        f"Upgrade the local Vibe-Skills installation for host {resolved_host_id} "
        "using the shared vgo-cli upgrade flow against the official default branch. "
        "Reinstall the supported host surface, verify the result, and report concise before-and-after status."
    )


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = os.urandom(4).hex()
    return f"{timestamp}-{suffix}"


def _resolve_artifact_root(repo_root: Path, artifact_root: str | Path | None) -> Path:
    if artifact_root in (None, ""):
        return (repo_root / ".vibeskills").resolve()

    artifact_root_path = Path(str(artifact_root)).expanduser()
    if artifact_root_path.is_absolute():
        return artifact_root_path.resolve()
    return (repo_root / artifact_root_path).resolve()


def _resolve_session_root(*, repo_root: Path, run_id: str, artifact_root: str | Path | None) -> Path:
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
    if force_runtime_neutral:
        raise RuntimeError("canonical entry requires PowerShell runtime bridge")

    shell = _resolve_powershell_host()
    if shell is None:
        raise RuntimeError("PowerShell executable not available in PATH")

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
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("canonical entry bridge returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("canonical entry bridge returned non-object payload")
    return payload


def assert_minimum_truth_artifacts(session_root: str | Path) -> dict[str, str]:
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
    force_runtime_neutral: bool = False,
) -> CanonicalLaunchResult:
    repo_root_path = Path(repo_root).resolve()
    requested_entry_id = _normalize_requested_entry_id(entry_id)
    effective_prompt = _resolve_effective_prompt(host_id=host_id, entry_id=requested_entry_id, prompt=prompt)
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
            artifact_root=artifact_root,
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
    parser = argparse.ArgumentParser(description="Launch canonical vibe entry and emit receipt-backed JSON output.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--host-id", default="codex")
    parser.add_argument("--entry-id", default="vibe")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--requested-stage-stop")
    parser.add_argument("--requested-grade-floor", choices=("L", "XL"))
    parser.add_argument("--run-id")
    parser.add_argument("--artifact-root")
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
        force_runtime_neutral=bool(args.force_runtime_neutral),
    )
    json.dump(result.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0
