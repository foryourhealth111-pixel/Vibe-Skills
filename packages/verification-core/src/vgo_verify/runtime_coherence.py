from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .policies import (
    default_coherence_runtime_config,
    load_json,
    merge_runtime_config,
    resolve_repo_root,
)
from .runtime_coherence_runtime import evaluate_runtime_coherence
from .runtime_coherence_support import (
    authoritative_gate_contains,
    content_contains,
    freshness_gate_sources,
    write_artifacts,
)


def runtime_config(governance: dict[str, Any]) -> dict[str, Any]:
    return merge_runtime_config(governance, default_coherence_runtime_config())


def evaluate(repo_root: Path, target_root: Path) -> dict[str, Any]:
    governance = load_json(repo_root / "config" / "version-governance.json")
    return evaluate_runtime_coherence(repo_root, target_root, runtime_config(governance))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral release/install/runtime coherence gate.")
    parser.add_argument("--target-root", default=str(Path.home() / ".codex"))
    parser.add_argument("--write-artifacts", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        repo_root = resolve_repo_root(Path(__file__))
        artifact = evaluate(repo_root, Path(args.target_root))
        if args.write_artifacts:
            write_artifacts(repo_root, artifact)
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0 if artifact["gate_result"] == "PASS" else 1
