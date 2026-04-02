from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .policies import load_json, resolve_repo_root, utc_now, write_text


def evaluate(repo_root: Path, report_paths: list[Path]) -> dict[str, Any]:
    reports = [load_json(path) for path in report_paths]
    failing_reports: list[str] = []
    manual_reports: list[str] = []
    blocked_completion_reports: list[str] = []

    for report_path, report in zip(report_paths, reports):
        summary = report.get("summary") or {}
        gate_result = str(summary.get("gate_result") or "")
        completion_language_allowed = bool(summary.get("completion_language_allowed"))
        if gate_result == "FAIL":
            failing_reports.append(str(report_path))
        elif gate_result == "MANUAL_REVIEW_REQUIRED":
            manual_reports.append(str(report_path))
        if not completion_language_allowed:
            blocked_completion_reports.append(str(report_path))

    gate_result = "PASS"
    if failing_reports:
        gate_result = "FAIL"
    elif manual_reports:
        gate_result = "MANUAL_REVIEW_REQUIRED"

    summary = {
        "gate_result": gate_result,
        "report_count": len(reports),
        "failing_report_count": len(failing_reports),
        "manual_review_report_count": len(manual_reports),
        "blocked_completion_report_count": len(blocked_completion_reports),
        "completion_language_allowed": gate_result == "PASS" and len(blocked_completion_reports) == 0,
    }
    return {
        "evaluated_at": utc_now(),
        "summary": summary,
        "reports": [
            {
                "path": str(report_path),
                "scenario_id": str((report.get("summary") or {}).get("scenario_id") or ""),
                "task_class": str((report.get("summary") or {}).get("task_class") or ""),
                "gate_result": str((report.get("summary") or {}).get("gate_result") or ""),
                "completion_language_allowed": bool((report.get("summary") or {}).get("completion_language_allowed")),
            }
            for report_path, report in zip(report_paths, reports)
        ],
        "failing_reports": failing_reports,
        "manual_review_reports": manual_reports,
        "blocked_completion_reports": blocked_completion_reports,
    }


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    json_path = output_root / "vibe-release-truth-gate.json"
    md_path = output_root / "vibe-release-truth-gate.md"
    write_text(json_path, json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# Vibe Release Truth Gate",
        "",
        f"- Gate Result: **{artifact['summary']['gate_result']}**",
        f"- Report Count: `{artifact['summary']['report_count']}`",
        f"- Failing Reports: `{artifact['summary']['failing_report_count']}`",
        f"- Manual Review Reports: `{artifact['summary']['manual_review_report_count']}`",
        f"- Completion Language Allowed: `{artifact['summary']['completion_language_allowed']}`",
        "",
        "## Reports",
        "",
    ]
    for report in artifact["reports"]:
        lines.append(
            f"- `{report['scenario_id']}` task_class=`{report['task_class']}` gate_result=`{report['gate_result']}` completion_language_allowed=`{report['completion_language_allowed']}`"
        )
    write_text(md_path, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate workflow acceptance reports into a release-truth decision.")
    parser.add_argument("--report", action="append", dest="reports", required=True, help="Path to a workflow acceptance report JSON file.")
    parser.add_argument("--repo-root", help="Optional explicit repository root.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else resolve_repo_root(Path(__file__))
    artifact = evaluate(repo_root, [Path(item).resolve() for item in args.reports])
    if args.write_artifacts:
        write_artifacts(repo_root, artifact, args.output_directory)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["summary"]["gate_result"] == "PASS" else 1
