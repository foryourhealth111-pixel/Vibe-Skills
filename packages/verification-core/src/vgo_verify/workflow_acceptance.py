from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .policies import load_json, resolve_repo_root, utc_now, write_text


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


def evaluate(repo_root: Path, scenario_path: Path) -> dict[str, Any]:
    contract = load_json(repo_root / "config" / "project-delivery-acceptance-contract.json")
    scenario = load_json(scenario_path)
    benchmark_repo_rel = str(scenario.get("benchmark_repo") or "").strip()
    benchmark_repo_path = (repo_root / benchmark_repo_rel).resolve() if benchmark_repo_rel else None
    benchmark_manifest_path = benchmark_repo_path / "acceptance-manifest.json" if benchmark_repo_path else None
    benchmark_manifest = load_json(benchmark_manifest_path) if benchmark_manifest_path and benchmark_manifest_path.exists() else None

    truth_layers = list(contract.get("truth_layers") or [])
    scenario_truths = scenario.get("truths") or {}
    truth_results: dict[str, dict[str, Any]] = {}

    failing_layers: list[str] = []
    manual_layers: list[str] = []
    incomplete_layers: list[str] = []

    for layer in truth_layers:
        layer_spec = scenario_truths.get(layer) or {}
        state = _normalize_truth_state(layer_spec.get("state", "not_run"))
        success = _truth_success(contract, state)
        completion_allowed = _truth_completion_allowed(contract, state)
        if state == "manual_review_required":
            manual_layers.append(layer)
        if not success:
            incomplete_layers.append(layer)
        if state in {"failing", "degraded", "partial", "not_run"}:
            failing_layers.append(layer)
        truth_results[layer] = {
            "state": state,
            "success": success,
            "completion_language_allowed": completion_allowed,
            "evidence": list(layer_spec.get("evidence") or []),
            "notes": str(layer_spec.get("notes") or ""),
        }

    runtime_status = str((scenario.get("runtime") or {}).get("status") or "").strip()
    readiness_state = str((scenario.get("runtime") or {}).get("readiness_state") or "").strip()
    forbidden_hits: list[dict[str, str]] = []
    for rule in list(contract.get("forbidden_completion_collapses") or []):
        source = str(rule.get("source") or "")
        value = str(rule.get("value") or "")
        if source == "runtime_status" and runtime_status == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})
        if source == "readiness_state" and readiness_state == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})

    gate_result = "PASS"
    if failing_layers or forbidden_hits:
        gate_result = "FAIL"
    elif manual_layers:
        gate_result = "MANUAL_REVIEW_REQUIRED"

    completion_language_allowed = gate_result == "PASS" and all(
        truth_results[layer]["completion_language_allowed"] for layer in truth_layers
    )

    summary = {
        "scenario_id": str(scenario.get("scenario_id") or ""),
        "task_class": str(scenario.get("task_class") or ""),
        "gate_result": gate_result,
        "completion_language_allowed": completion_language_allowed,
        "runtime_status": runtime_status,
        "readiness_state": readiness_state,
        "manual_review_layer_count": len(manual_layers),
        "failing_layer_count": len(failing_layers),
        "forbidden_completion_hit_count": len(forbidden_hits),
        "incomplete_layers": incomplete_layers,
        "benchmark_repo_rel": benchmark_repo_rel,
        "benchmark_repo_exists": bool(benchmark_repo_path and benchmark_repo_path.exists()),
        "benchmark_manifest_exists": bool(benchmark_manifest_path and benchmark_manifest_path.exists()),
    }

    if benchmark_repo_rel and not summary["benchmark_repo_exists"]:
        summary["gate_result"] = "FAIL"
        summary["completion_language_allowed"] = False
        summary["incomplete_layers"] = sorted(set(summary["incomplete_layers"] + ["product_acceptance_truth"]))
    if benchmark_repo_rel and summary["benchmark_repo_exists"] and not summary["benchmark_manifest_exists"]:
        if summary["gate_result"] == "PASS":
            summary["gate_result"] = "MANUAL_REVIEW_REQUIRED"
        summary["completion_language_allowed"] = False
        summary["incomplete_layers"] = sorted(set(summary["incomplete_layers"] + ["product_acceptance_truth"]))

    manual_spot_checks = list(scenario.get("manual_spot_checks") or [])
    residual_risks = list(scenario.get("residual_risks") or [])

    return {
        "evaluated_at": utc_now(),
        "contract_id": str(contract.get("contract_id") or ""),
        "contract_version": int(contract.get("version") or 0),
        "scenario_path": str(scenario_path),
        "summary": summary,
        "benchmark": {
            "repo_rel": benchmark_repo_rel,
            "repo_path": str(benchmark_repo_path) if benchmark_repo_path else "",
            "repo_exists": bool(benchmark_repo_path and benchmark_repo_path.exists()),
            "manifest_path": str(benchmark_manifest_path) if benchmark_manifest_path else "",
            "manifest_exists": bool(benchmark_manifest_path and benchmark_manifest_path.exists()),
            "manifest": benchmark_manifest,
        },
        "truth_results": truth_results,
        "forbidden_completion_hits": forbidden_hits,
        "manual_spot_checks": manual_spot_checks,
        "residual_risks": residual_risks,
    }


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    json_path = output_root / "vibe-workflow-acceptance-gate.json"
    md_path = output_root / "vibe-workflow-acceptance-gate.md"
    write_text(json_path, json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Vibe Workflow Acceptance Gate",
        "",
        f"- Scenario: `{artifact['summary']['scenario_id']}`",
        f"- Task Class: `{artifact['summary']['task_class']}`",
        f"- Gate Result: **{artifact['summary']['gate_result']}**",
        f"- Completion Language Allowed: `{artifact['summary']['completion_language_allowed']}`",
        f"- Runtime Status: `{artifact['summary']['runtime_status']}`",
        f"- Readiness State: `{artifact['summary']['readiness_state']}`",
        f"- Benchmark Repo: `{artifact['summary']['benchmark_repo_rel']}`",
        f"- Benchmark Repo Exists: `{artifact['summary']['benchmark_repo_exists']}`",
        f"- Benchmark Manifest Exists: `{artifact['summary']['benchmark_manifest_exists']}`",
        f"- Manual Review Layers: `{artifact['summary']['manual_review_layer_count']}`",
        f"- Failing Layers: `{artifact['summary']['failing_layer_count']}`",
        f"- Forbidden Completion Hits: `{artifact['summary']['forbidden_completion_hit_count']}`",
        "",
        "## Truth Layers",
        "",
    ]
    for layer, info in artifact["truth_results"].items():
        lines.append(
            f"- `{layer}`: state=`{info['state']}` success=`{info['success']}` completion_language_allowed=`{info['completion_language_allowed']}`"
        )
    if artifact["forbidden_completion_hits"]:
        lines += ["", "## Forbidden Completion Hits", ""]
        for hit in artifact["forbidden_completion_hits"]:
            lines.append(f"- `{hit['source']}`=`{hit['value']}` reason=`{hit['reason']}`")
    if artifact["benchmark"]["manifest"]:
        lines += ["", "## Benchmark Manifest", ""]
        manifest = artifact["benchmark"]["manifest"]
        lines.append(f"- `benchmark_id`: `{manifest.get('benchmark_id', '')}`")
        for flow in list(manifest.get("critical_user_flows") or []):
            lines.append(f"- critical_user_flow: {flow}")
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
    parser = argparse.ArgumentParser(description="Evaluate downstream project delivery acceptance for a governed scenario.")
    parser.add_argument("--scenario", required=True, help="Path to the scenario JSON file.")
    parser.add_argument("--repo-root", help="Optional explicit repository root.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else resolve_repo_root(Path(__file__))
    artifact = evaluate(repo_root, Path(args.scenario).resolve())
    if args.write_artifacts:
        write_artifacts(repo_root, artifact, args.output_directory)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["summary"]["gate_result"] == "PASS" else 1
