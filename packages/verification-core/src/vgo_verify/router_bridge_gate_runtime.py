from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .router_bridge_gate_support import load_json, utc_now


def run_bridge(repo_root: Path, prompt: str, grade: str, task_type: str) -> dict[str, Any]:
    bridge = repo_root / "scripts" / "router" / "invoke-pack-route.py"
    command = [
        sys.executable,
        str(bridge),
        "--prompt",
        prompt,
        "--grade",
        grade,
        "--task-type",
        task_type,
        "--force-runtime-neutral",
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def evaluate_router_bridge(repo_root: Path) -> dict[str, Any]:
    route_fixture = load_json(repo_root / "tests" / "replay" / "route" / "recovery-wave-curated-prompts.json")
    platform_fixture = load_json(repo_root / "tests" / "replay" / "platform" / "linux-without-pwsh.json")

    assertions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    def record(condition: bool, message: str) -> None:
        print(f"[{'PASS' if condition else 'FAIL'}] {message}")
        assertions.append({"ok": condition, "message": message})

    record(platform_fixture["lane"] == "linux_without_pwsh", "platform fixture lane is linux_without_pwsh")
    record(platform_fixture["constraints"]["force_runtime_neutral"] is True, "platform fixture requires runtime-neutral execution")

    required_fields = set(platform_fixture["constraints"]["required_contract_fields"])
    for case in route_fixture["cases"]:
        result = run_bridge(repo_root, case["prompt"], case["grade"], case["task_type"])
        observed_fields = set(result.keys())
        missing_fields = sorted(required_fields - observed_fields)
        expected = case["expected"]
        expected_modes = expected.get("allowed_route_modes") or ([expected["route_mode"]] if expected.get("route_mode") else [])
        selected = result.get("selected") or {}
        ok = (
            not missing_fields
            and (not expected_modes or result.get("route_mode") in expected_modes)
            and (expected.get("selected_pack") is None or selected.get("pack_id") == expected.get("selected_pack"))
            and (expected.get("selected_skill") is None or selected.get("skill") == expected.get("selected_skill"))
        )
        record(ok, f"{case['id']} satisfies runtime-neutral route expectation")
        results.append(
            {
                "id": case["id"],
                "prompt": case["prompt"],
                "route_mode": result.get("route_mode"),
                "route_reason": result.get("route_reason"),
                "selected_pack": selected.get("pack_id"),
                "selected_skill": selected.get("skill"),
                "missing_fields": missing_fields,
            }
        )

    failures = sum(1 for item in assertions if not item["ok"])
    return {
        "gate": "runtime-neutral-router-bridge-gate",
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "gate_result": "PASS" if failures == 0 else "FAIL",
        "assertions": assertions,
        "results": results,
        "summary": {
            "failures": failures,
            "total_assertions": len(assertions),
        },
    }
