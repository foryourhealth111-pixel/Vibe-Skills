#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from runpy import run_path

ensure_verification_core_src_on_path = run_path(str(Path(__file__).with_name('_bootstrap.py')))['ensure_verification_core_src_on_path']
ensure_verification_core_src_on_path()

from vgo_verify.runtime_freshness import GovernanceContext, evaluate_freshness, load_governance_context, main, parse_args, runtime_config

__all__ = [
    'GovernanceContext',
    'evaluate_freshness',
    'load_governance_context',
    'main',
    'parse_args',
    'runtime_config',
]

if __name__ == '__main__':
    raise SystemExit(main())
