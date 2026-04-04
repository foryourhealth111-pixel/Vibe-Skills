from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .policies import load_json


@dataclass(slots=True)
class GateCheckResult:
    id: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioRunResult:
    name: str
    passed: bool
    checks: list[GateCheckResult] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


CheckRunner = Callable[[dict[str, Any]], GateCheckResult]


def _contract_check(spec: dict[str, Any]) -> GateCheckResult:
    required_fields = ("id", "kind", "owner", "entrypoint")
    missing = [field for field in required_fields if not str(spec.get(field) or "").strip()]
    return GateCheckResult(
        id=str(spec.get("id") or "unnamed"),
        passed=len(missing) == 0,
        details={
            "kind": str(spec.get("kind") or ""),
            "owner": str(spec.get("owner") or ""),
            "entrypoint": str(spec.get("entrypoint") or ""),
            "missing_fields": missing,
        },
    )


class GateEngine:
    def __init__(
        self,
        scenario_dir: Path | None = None,
        registry: dict[str, CheckRunner] | None = None,
    ) -> None:
        self.scenario_dir = scenario_dir or Path(__file__).resolve().parent / "scenarios"
        self.registry = registry or {"contract": _contract_check}

    def load(self, name: str) -> dict[str, Any]:
        path = self.scenario_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"verification scenario not found: {path}")
        payload = load_json(path)
        payload.setdefault("name", name)
        payload.setdefault("checks", [])
        return payload

    def run(self, name: str) -> ScenarioRunResult:
        scenario = self.load(name)
        check_results: list[GateCheckResult] = []
        for spec in list(scenario.get("checks") or []):
            kind = str(spec.get("kind") or "contract")
            if kind not in self.registry:
                check_results.append(
                    GateCheckResult(
                        id=str(spec.get("id") or kind),
                        passed=False,
                        details={"error": f"unknown check kind: {kind}"},
                    )
                )
                continue
            check_results.append(self.registry[kind](spec))
        return ScenarioRunResult(
            name=str(scenario.get("name") or name),
            passed=all(item.passed for item in check_results),
            checks=check_results,
            details={"description": str(scenario.get("description") or "")},
        )
