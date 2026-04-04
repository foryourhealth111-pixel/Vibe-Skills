#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .opencode_preview_smoke_runtime import evaluate_opencode_preview
from .opencode_preview_smoke_support import (
    EXPECTED_FILES,
    detect_skill_hit,
    run,
    skill_output_looks_truncated,
    write_json,
)


def evaluate(repo_root: Path, write_artifacts: bool = False) -> dict[str, object]:
    return evaluate_opencode_preview(repo_root, write_artifacts=write_artifacts)



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--write-artifacts', action='store_true')
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    payload = evaluate(repo_root, write_artifacts=args.write_artifacts)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not payload['failures'] else 1


if __name__ == '__main__':
    sys.exit(main())
