#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .release_notes_quality_runtime import evaluate_note, evaluate_release_notes
from .release_notes_quality_support import (
    REQUIRED_HEADINGS,
    default_release_note_path,
    load_governance,
    resolve_repo_root,
    write_artifacts,
)


evaluate = evaluate_release_notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release note structure and quality invariants.")
    parser.add_argument("--repo-root", help="Optional explicit repository root.")
    parser.add_argument("--path", action="append", dest="paths", help="Optional explicit release note path. Defaults to the current governed release note.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else resolve_repo_root(Path(__file__))
    note_paths = [Path(item).resolve() for item in args.paths] if args.paths else [default_release_note_path(repo_root)]
    artifact = evaluate(repo_root, note_paths)
    if args.write_artifacts:
        write_artifacts(repo_root, artifact, args.output_directory)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["summary"]["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
