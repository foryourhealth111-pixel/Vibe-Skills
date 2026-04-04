from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .policies import write_text


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
