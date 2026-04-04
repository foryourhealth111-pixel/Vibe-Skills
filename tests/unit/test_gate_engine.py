from __future__ import annotations

import sys
from pathlib import Path


def _add_src_to_path() -> None:
    src = Path(__file__).resolve().parents[2] / "packages" / "verification-core" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from vgo_verify.gate_engine import GateEngine


def test_gate_engine_runs_named_scenario() -> None:
    engine = GateEngine()
    result = engine.run("install_matrix")
    assert result.name == "install_matrix"
    assert result.passed is True
    assert result.checks
