from __future__ import annotations

import sys
from pathlib import Path


def _add_src_to_path() -> None:
    src = Path(__file__).resolve().parents[2] / "packages" / "verification-core" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from vgo_verify.gate_engine import GateEngine
from vgo_verify.scenario_runner import run_named_scenario


def test_scenario_runner_returns_named_runtime_matrix() -> None:
    engine = GateEngine()
    result = run_named_scenario("runtime_matrix", engine=engine)
    assert result.name == "runtime_matrix"
    assert result.passed is True
    assert len(result.checks) >= 2
