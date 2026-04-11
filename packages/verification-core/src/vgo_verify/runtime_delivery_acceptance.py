#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .runtime_delivery_acceptance_runtime import evaluate_delivery_acceptance
from .runtime_delivery_acceptance_support import (
    resolve_repo_root,
    write_text,
)


def evaluate(repo_root: Path, session_root: Path) -> dict[str, Any]:
    return evaluate_delivery_acceptance(repo_root, session_root)


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
    frozen_sections = artifact.get("frozen_requirement_sections") or {}
    if frozen_sections.get("artifact_review_requirements"):
        lines += ["", "## Frozen Artifact Review Requirements", ""]
        for item in frozen_sections["artifact_review_requirements"]:
            lines.append(f"- {item}")
    if frozen_sections.get("code_task_tdd_evidence_requirements"):
        lines += ["", "## Frozen Code Task TDD Evidence Requirements", ""]
        for item in frozen_sections["code_task_tdd_evidence_requirements"]:
            lines.append(f"- {item}")
    if frozen_sections.get("code_task_tdd_exceptions"):
        lines += ["", "## Frozen Code Task TDD Exceptions", ""]
        for item in frozen_sections["code_task_tdd_exceptions"]:
            lines.append(f"- {item}")
    if frozen_sections.get("baseline_document_quality_dimensions"):
        lines += ["", "## Frozen Baseline Document Quality Dimensions", ""]
        for item in frozen_sections["baseline_document_quality_dimensions"]:
            lines.append(f"- {item}")
    if frozen_sections.get("baseline_ui_quality_dimensions"):
        lines += ["", "## Frozen Baseline UI Quality Dimensions", ""]
        for item in frozen_sections["baseline_ui_quality_dimensions"]:
            lines.append(f"- {item}")
    if frozen_sections.get("task_specific_acceptance_extensions"):
        lines += ["", "## Frozen Task-Specific Acceptance Extensions", ""]
        for item in frozen_sections["task_specific_acceptance_extensions"]:
            lines.append(f"- {item}")
    if frozen_sections.get("research_augmentation_sources"):
        lines += ["", "## Frozen Research Augmentation Sources", ""]
        for item in frozen_sections["research_augmentation_sources"]:
            lines.append(f"- {item}")
    coverage = artifact.get("artifact_review_coverage") or {}
    tdd_coverage = artifact.get("tdd_evidence_coverage") or {}
    if any(
        tdd_coverage.get(key)
        for key in (
            "covered_code_task_tdd_evidence_requirements",
            "missing_code_task_tdd_evidence_requirements",
            "covered_code_task_tdd_exceptions",
            "missing_code_task_tdd_exceptions",
            "red_phase_evidence_paths",
            "green_phase_evidence_paths",
            "refactor_phase_evidence_paths",
        )
    ):
        lines += ["", "## Code Task TDD Evidence Coverage", ""]
        for item in tdd_coverage.get("covered_code_task_tdd_evidence_requirements") or []:
            lines.append(f"- Covered code-task TDD evidence requirement: {item}")
        for item in tdd_coverage.get("missing_code_task_tdd_evidence_requirements") or []:
            lines.append(f"- Missing code-task TDD evidence requirement: {item}")
        for item in tdd_coverage.get("covered_code_task_tdd_exceptions") or []:
            lines.append(f"- Covered code-task TDD exception: {item}")
        for item in tdd_coverage.get("missing_code_task_tdd_exceptions") or []:
            lines.append(f"- Missing code-task TDD exception: {item}")
        for item in tdd_coverage.get("red_phase_evidence_paths") or []:
            lines.append(f"- Red-phase evidence: {item}")
        for item in tdd_coverage.get("green_phase_evidence_paths") or []:
            lines.append(f"- Green-phase evidence: {item}")
        for item in tdd_coverage.get("refactor_phase_evidence_paths") or []:
            lines.append(f"- Refactor-phase evidence: {item}")
    if any(
        coverage.get(key)
        for key in (
            "covered_baseline_document_quality_dimensions",
            "missing_baseline_document_quality_dimensions",
            "covered_baseline_ui_quality_dimensions",
            "missing_baseline_ui_quality_dimensions",
            "covered_task_specific_acceptance_extensions",
            "missing_task_specific_acceptance_extensions",
            "considered_research_augmentation_sources",
            "missing_research_augmentation_sources",
        )
    ):
        lines += ["", "## Artifact Review Coverage", ""]
        for item in coverage.get("covered_baseline_document_quality_dimensions") or []:
            lines.append(f"- Covered baseline document quality dimension: {item}")
        for item in coverage.get("missing_baseline_document_quality_dimensions") or []:
            lines.append(f"- Missing baseline document quality dimension: {item}")
        for item in coverage.get("covered_baseline_ui_quality_dimensions") or []:
            lines.append(f"- Covered baseline UI quality dimension: {item}")
        for item in coverage.get("missing_baseline_ui_quality_dimensions") or []:
            lines.append(f"- Missing baseline UI quality dimension: {item}")
        for item in coverage.get("covered_task_specific_acceptance_extensions") or []:
            lines.append(f"- Covered task-specific acceptance: {item}")
        for item in coverage.get("missing_task_specific_acceptance_extensions") or []:
            lines.append(f"- Missing task-specific acceptance: {item}")
        for item in coverage.get("considered_research_augmentation_sources") or []:
            lines.append(f"- Considered research source: {item}")
        for item in coverage.get("missing_research_augmentation_sources") or []:
            lines.append(f"- Missing research source: {item}")
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
