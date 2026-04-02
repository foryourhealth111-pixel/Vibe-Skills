#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "packages" / "verification-core" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vgo_verify.runtime_freshness import GovernanceContext, evaluate_freshness, load_governance_context, main, parse_args, runtime_config

__all__ = [
    "GovernanceContext",
    "evaluate_freshness",
    "load_governance_context",
    "main",
    "parse_args",
    "runtime_config",
]

if __name__ == "__main__":
    raise SystemExit(main())
