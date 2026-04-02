from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .gate_engine import GateEngine, ScenarioRunResult


def run_named_scenario(name: str, engine: GateEngine | None = None) -> ScenarioRunResult:
    active_engine = engine or GateEngine()
    return active_engine.run(name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a named verification-core scenario.")
    parser.add_argument("scenario_name", help="Scenario definition name without .json suffix.")
    args = parser.parse_args()
    result = run_named_scenario(args.scenario_name)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.passed else 1
