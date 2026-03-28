#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


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


def _normalize_truth_state(state: str) -> str:
    normalized = str(state or "").strip().lower()
    aliases = {
        "pass": "passing",
        "passed": "passing",
        "ok": "passing",
        "manual": "manual_review_required",
        "manual_required": "manual_review_required",
        "manual_review": "manual_review_required",
        "fail": "failing",
        "failed": "failing",
    }
    return aliases.get(normalized, normalized)


def _truth_success(contract: dict[str, Any], state: str) -> bool:
    return bool(((contract.get("truth_states") or {}).get(state) or {}).get("counts_as_success"))


def _truth_completion_allowed(contract: dict[str, Any], state: str) -> bool:
    return bool(((contract.get("truth_states") or {}).get(state) or {}).get("completion_language_allowed"))


def _read_text_if_exists(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_bullets(text: str, heading: str) -> list[str]:
    section = _extract_section(text, heading)
    bullets: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _manual_spot_checks_from_requirement(requirement_text: str) -> tuple[list[str], bool]:
    raw_items = _extract_bullets(requirement_text, "Manual Spot Checks")
    if not raw_items:
        return [], True

    normalized_items = [item.strip() for item in raw_items if item.strip()]
    if len(normalized_items) == 1:
        lowered = normalized_items[0].lower()
        if lowered.startswith("none required") or lowered.startswith("no manual spot checks required"):
            return [], False

    return normalized_items, False


def _derive_readiness_state(gate_result: str, manual_spot_checks: list[str]) -> str:
    if gate_result == "PASS":
        return "fully_ready"
    if gate_result == "MANUAL_REVIEW_REQUIRED" or manual_spot_checks:
        return "manual_actions_pending"
    return "verification_failed"


def evaluate(repo_root: Path, session_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / "config" / "project-delivery-acceptance-contract.json")
    execute_receipt_path = session_root / "phase-execute.json"
    cleanup_receipt_path = session_root / "cleanup-receipt.json"

    execute_receipt = load_json(execute_receipt_path)
    cleanup_receipt = load_json(cleanup_receipt_path)

    requirement_doc_path = Path(str(execute_receipt.get("requirement_doc_path") or ""))
    execution_plan_path = Path(str(execute_receipt.get("execution_plan_path") or ""))
    execution_manifest_path = Path(str(execute_receipt.get("execution_manifest_path") or ""))
    runtime_input_packet_path = Path(str(execute_receipt.get("runtime_input_packet_path") or ""))

    requirement_text = _read_text_if_exists(requirement_doc_path)
    execution_plan_text = _read_text_if_exists(execution_plan_path)
    execution_manifest = load_json(execution_manifest_path)
    runtime_input_packet = load_json(runtime_input_packet_path) if runtime_input_packet_path.exists() else {}

    product_acceptance_criteria = _extract_bullets(requirement_text, "Product Acceptance Criteria")
    manual_spot_checks, manual_section_missing = _manual_spot_checks_from_requirement(requirement_text)
    completion_language_policy = _extract_bullets(requirement_text, "Completion Language Policy")
    delivery_truth_contract = _extract_bullets(requirement_text, "Delivery Truth Contract")

    governance_truth_state = "passing"
    governance_truth_notes: list[str] = []
    required_artifacts = [
        execute_receipt_path,
        cleanup_receipt_path,
        requirement_doc_path,
        execution_plan_path,
        execution_manifest_path,
    ]
    missing_artifacts = [str(path) for path in required_artifacts if not path.exists()]
    if missing_artifacts:
        governance_truth_state = "failing"
        governance_truth_notes.append("Required runtime artifacts are missing.")
    elif str((runtime_input_packet.get("authority_flags") or {}).get("explicit_runtime_skill") or "vibe") != "vibe":
        governance_truth_state = "degraded"
        governance_truth_notes.append("Runtime authority drifted away from vibe.")
    elif str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        governance_truth_state = "degraded"
        governance_truth_notes.append("Cleanup degraded before closure.")

    execution_status = str(execution_manifest.get("status") or "")
    failed_unit_count = int(execution_manifest.get("failed_unit_count") or 0)
    timed_out_unit_count = int(execution_manifest.get("timed_out_unit_count") or 0)
    executed_unit_count = int(execution_manifest.get("executed_unit_count") or 0)

    engineering_truth_state = "passing"
    engineering_truth_notes: list[str] = []
    if executed_unit_count == 0 or execution_status == "failed":
        engineering_truth_state = "failing"
        engineering_truth_notes.append("No executable verification path completed successfully.")
    elif execution_status == "completed_with_failures" or failed_unit_count > 0 or timed_out_unit_count > 0:
        engineering_truth_state = "partial"
        engineering_truth_notes.append("Execution verification completed with failing or timed-out units.")

    workflow_truth_state = "passing"
    workflow_truth_notes: list[str] = []
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        workflow_truth_state = "degraded"
        workflow_truth_notes.append("Cleanup degraded, so workflow closure is not fully authoritative.")
    elif execution_status == "completed_local_scope" or not bool(execute_receipt.get("completion_claim_allowed")):
        workflow_truth_state = "partial"
        workflow_truth_notes.append("This run closed only a bounded local scope, not the full root task.")
    elif execution_status == "completed_with_failures":
        workflow_truth_state = "partial"
        workflow_truth_notes.append("Workflow closed with failed units still present.")
    elif execution_status != "completed":
        workflow_truth_state = "failing"
        workflow_truth_notes.append("Workflow did not reach a clean completed state.")

    product_truth_state = "passing"
    product_truth_notes: list[str] = []
    if engineering_truth_state in {"failing", "degraded"}:
        product_truth_state = "failing"
        product_truth_notes.append("Engineering verification truth is not strong enough to support product acceptance.")
    elif engineering_truth_state == "partial":
        product_truth_state = "partial"
        product_truth_notes.append("Product acceptance cannot pass while engineering verification remains partial.")
    elif not product_acceptance_criteria:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Requirement doc is missing frozen product acceptance criteria.")
    elif manual_section_missing:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Requirement doc did not declare whether manual spot checks are needed.")
    elif manual_spot_checks:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Frozen manual spot checks remain pending.")

    truth_layers = {
        "governance_truth": {
            "state": _normalize_truth_state(governance_truth_state),
            "evidence": [str(path) for path in required_artifacts if path.exists()],
            "notes": " ".join(governance_truth_notes).strip(),
        },
        "engineering_verification_truth": {
            "state": _normalize_truth_state(engineering_truth_state),
            "evidence": [str(execution_manifest_path)],
            "notes": " ".join(engineering_truth_notes).strip(),
        },
        "workflow_completion_truth": {
            "state": _normalize_truth_state(workflow_truth_state),
            "evidence": [str(execute_receipt_path), str(cleanup_receipt_path)],
            "notes": " ".join(workflow_truth_notes).strip(),
        },
        "product_acceptance_truth": {
            "state": _normalize_truth_state(product_truth_state),
            "evidence": [str(requirement_doc_path)],
            "notes": " ".join(product_truth_notes).strip(),
        },
    }

    failing_layers = [
        layer
        for layer, info in truth_layers.items()
        if info["state"] in {"failing", "degraded", "partial", "not_run"}
    ]
    manual_layers = [layer for layer, info in truth_layers.items() if info["state"] == "manual_review_required"]
    incomplete_layers = [layer for layer, info in truth_layers.items() if not _truth_success(contract, info["state"])]

    gate_result = "PASS"
    if failing_layers:
        gate_result = "FAIL"
    elif manual_layers:
        gate_result = "MANUAL_REVIEW_REQUIRED"

    readiness_state = _derive_readiness_state(gate_result, manual_spot_checks)
    forbidden_hits: list[dict[str, str]] = []
    for rule in list(contract.get("forbidden_completion_collapses") or []):
        source = str(rule.get("source") or "")
        value = str(rule.get("value") or "")
        if source == "runtime_status" and execution_status == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})
        if source == "readiness_state" and readiness_state == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})

    completion_language_allowed = gate_result == "PASS" and not forbidden_hits and all(
        _truth_completion_allowed(contract, info["state"]) for info in truth_layers.values()
    )

    residual_risks: list[str] = []
    if failed_unit_count > 0:
        residual_risks.append(f"{failed_unit_count} execution unit(s) failed.")
    if timed_out_unit_count > 0:
        residual_risks.append(f"{timed_out_unit_count} execution unit(s) timed out.")
    if manual_spot_checks:
        residual_risks.append("Manual spot checks remain pending.")
    if manual_section_missing:
        residual_risks.append("Manual spot check policy was not frozen in the requirement doc.")
    if not product_acceptance_criteria:
        residual_risks.append("Product acceptance criteria were not frozen in the requirement doc.")
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        residual_risks.append("Cleanup degraded, so closure is not fully authoritative.")
    if execution_status == "completed_local_scope":
        residual_risks.append("This run is child-scoped and cannot justify root-level completion wording.")

    summary = {
        "gate_result": gate_result,
        "completion_language_allowed": completion_language_allowed,
        "runtime_status": execution_status,
        "readiness_state": readiness_state,
        "manual_review_layer_count": len(manual_layers),
        "failing_layer_count": len(failing_layers),
        "forbidden_completion_hit_count": len(forbidden_hits),
        "incomplete_layers": incomplete_layers,
        "manual_spot_check_count": len(manual_spot_checks),
    }

    return {
        "evaluated_at": utc_now(),
        "contract_id": str(contract.get("contract_id") or ""),
        "contract_version": int(contract.get("version") or 0),
        "session_root": str(session_root),
        "artifacts": {
            "execute_receipt_path": str(execute_receipt_path),
            "cleanup_receipt_path": str(cleanup_receipt_path),
            "requirement_doc_path": str(requirement_doc_path),
            "execution_plan_path": str(execution_plan_path),
            "execution_manifest_path": str(execution_manifest_path),
            "runtime_input_packet_path": str(runtime_input_packet_path),
        },
        "summary": summary,
        "truth_results": {
            layer: {
                "state": info["state"],
                "success": _truth_success(contract, info["state"]),
                "completion_language_allowed": _truth_completion_allowed(contract, info["state"]),
                "evidence": info["evidence"],
                "notes": info["notes"],
            }
            for layer, info in truth_layers.items()
        },
        "frozen_requirement_sections": {
            "product_acceptance_criteria": product_acceptance_criteria,
            "manual_spot_checks": manual_spot_checks,
            "completion_language_policy": completion_language_policy,
            "delivery_truth_contract": delivery_truth_contract,
        },
        "execution_context": {
            "governance_scope": str(execution_manifest.get("governance_scope") or ""),
            "completion_claim_allowed": bool(execute_receipt.get("completion_claim_allowed")),
            "cleanup_mode": str(cleanup_receipt.get("cleanup_mode") or ""),
            "execution_status": execution_status,
            "executed_unit_count": executed_unit_count,
            "failed_unit_count": failed_unit_count,
            "timed_out_unit_count": timed_out_unit_count,
            "execution_plan_contains_delivery_acceptance_plan": "## Delivery Acceptance Plan" in execution_plan_text,
        },
        "forbidden_completion_hits": forbidden_hits,
        "manual_spot_checks": manual_spot_checks,
        "residual_risks": residual_risks,
    }


def write_artifacts(artifact: dict[str, Any], output_directory: Path) -> None:
    json_path = output_directory / "delivery-acceptance-report.json"
    md_path = output_directory / "delivery-acceptance-report.md"
    write_text(json_path, json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Runtime Delivery Acceptance Report",
        "",
        f"- Gate Result: **{artifact['summary']['gate_result']}**",
        f"- Completion Language Allowed: `{artifact['summary']['completion_language_allowed']}`",
        f"- Runtime Status: `{artifact['summary']['runtime_status']}`",
        f"- Readiness State: `{artifact['summary']['readiness_state']}`",
        f"- Manual Spot Checks Pending: `{artifact['summary']['manual_spot_check_count']}`",
        f"- Failing Layers: `{artifact['summary']['failing_layer_count']}`",
        "",
        "## Truth Layers",
        "",
    ]
    for layer, info in artifact["truth_results"].items():
        lines.append(
            f"- `{layer}`: state=`{info['state']}` success=`{info['success']}` completion_language_allowed=`{info['completion_language_allowed']}`"
        )
    if artifact["manual_spot_checks"]:
        lines += ["", "## Manual Spot Checks", ""]
        for item in artifact["manual_spot_checks"]:
            lines.append(f"- {item}")
    if artifact["residual_risks"]:
        lines += ["", "## Residual Risks", ""]
        for item in artifact["residual_risks"]:
            lines.append(f"- {item}")
    write_text(md_path, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate main-chain downstream delivery acceptance for a governed vibe session.")
    parser.add_argument("--session-root", required=True, help="Path to outputs/runtime/vibe-sessions/<run-id>.")
    parser.add_argument("--repo-root", help="Optional explicit repository root.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else resolve_repo_root(Path(__file__))
    session_root = Path(args.session_root).resolve()
    artifact = evaluate(repo_root, session_root)
    if args.write_artifacts:
        output_directory = Path(args.output_directory).resolve() if args.output_directory else session_root
        write_artifacts(artifact, output_directory)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["summary"]["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
