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
