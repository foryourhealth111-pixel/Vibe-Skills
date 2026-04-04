from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policies import resolve_repo_root
from .workflow_acceptance_runtime import evaluate_workflow_acceptance
from .workflow_acceptance_support import write_artifacts


evaluate = evaluate_workflow_acceptance


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


if __name__ == "__main__":
    raise SystemExit(main())
