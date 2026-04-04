#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .router_bridge_gate_runtime import evaluate_router_bridge, run_bridge
from .router_bridge_gate_support import resolve_repo_root, write_artifacts


evaluate = evaluate_router_bridge


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the runtime-neutral router bridge against curated recovery prompts.")
    parser.add_argument("--write-artifacts", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = resolve_repo_root(Path(__file__))
    artifact = evaluate(repo_root)
    if args.write_artifacts:
        write_artifacts(repo_root, artifact)
    return 0 if artifact["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
