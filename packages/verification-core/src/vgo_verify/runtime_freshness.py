from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .policies import (
    GovernanceContext,
    default_freshness_runtime_config,
    load_governance_context as _load_governance_context,
    merge_runtime_config,
)
from .runtime_freshness_runtime import evaluate_freshness_runtime
from .runtime_freshness_support import (
    build_freshness_context,
    write_freshness_artifacts,
    write_freshness_receipt,
)


def runtime_config(governance: dict[str, Any]) -> dict[str, Any]:
    return merge_runtime_config(governance, default_freshness_runtime_config())



def load_governance_context(script_path: Path, enforce_context: bool = True) -> GovernanceContext:
    return _load_governance_context(script_path, default_freshness_runtime_config(), enforce_context=enforce_context)



def evaluate_freshness(
    repo_root: Path,
    governance: dict[str, Any],
    canonical_root: Path,
    target_root: Path,
    script_path: Path,
    write_artifacts: bool = False,
    write_receipt: bool = False,
) -> tuple[bool, dict[str, Any]]:
    context = build_freshness_context(
        repo_root=repo_root,
        governance=governance,
        canonical_root=canonical_root,
        target_root=target_root,
        runtime=runtime_config(governance),
    )
    gate_pass, artifact = evaluate_freshness_runtime(context, script_path)

    if write_artifacts:
        write_freshness_artifacts(repo_root, artifact)

    if write_receipt:
        write_freshness_receipt(context, gate_pass, artifact)

    return gate_pass, artifact



def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Runtime-neutral installed runtime freshness gate.')
    parser.add_argument('--target-root', default=str(Path.home() / '.codex'))
    parser.add_argument('--write-artifacts', action='store_true')
    parser.add_argument('--write-receipt', action='store_true')
    return parser.parse_args(argv)



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    script_path = Path(__file__)
    try:
        context = load_governance_context(script_path, enforce_context=True)
        gate_pass, _ = evaluate_freshness(
            repo_root=context.repo_root,
            governance=context.governance,
            canonical_root=context.canonical_root,
            target_root=Path(args.target_root),
            script_path=script_path,
            write_artifacts=args.write_artifacts,
            write_receipt=args.write_receipt,
        )
    except Exception as exc:  # pragma: no cover
        print(f'[FAIL] {exc}', file=sys.stderr)
        return 1
    return 0 if gate_pass else 1
