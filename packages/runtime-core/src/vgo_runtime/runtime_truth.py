from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_skill_routing_projection(
    *,
    skill_routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if skill_routing is None:
        routing: dict[str, Any] = {}
    elif isinstance(skill_routing, dict):
        routing = dict(skill_routing)
    else:
        raise ValueError("skill_routing must be an object when present")

    schema_version = routing.get("schema_version")
    if schema_version is None:
        normalized_schema_version = "simplified_skill_routing_v1"
    elif isinstance(schema_version, str) and schema_version.strip():
        normalized_schema_version = schema_version
    else:
        raise ValueError("skill_routing.schema_version must be a non-empty string when present")

    candidates = routing.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("skill_routing.candidates must be a list when present")

    rejected = routing.get("rejected", [])
    if not isinstance(rejected, list):
        raise ValueError("skill_routing.rejected must be a list when present")

    return {
        "schema_version": normalized_schema_version,
        "candidates": list(candidates),
        "rejected": list(rejected),
    }


def build_runtime_truth_packet(
    *,
    run_id: str,
    task: str,
    module_assignments: dict[str, Any],
    base_fields: dict[str, Any] | None = None,
    skill_routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(base_fields or {})
    payload.pop("skill_selection", None)
    payload["stage"] = "runtime_input_freeze"
    payload["run_id"] = run_id
    payload["task"] = task
    payload["module_assignments"] = module_assignments
    payload["skill_routing"] = build_skill_routing_projection(
        skill_routing=skill_routing,
    )
    return payload


def build_runtime_truth_packet_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("runtime truth build payload must be an object")

    run_id = payload.get("run_id")
    task = payload.get("task")
    module_assignments = payload.get("module_assignments")
    base_fields = payload.get("base_fields")
    skill_routing = payload.get("skill_routing")

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("runtime truth build payload missing run_id")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("runtime truth build payload missing task")
    if not isinstance(module_assignments, dict):
        raise ValueError("runtime truth build payload missing module_assignments")
    if base_fields is not None and not isinstance(base_fields, dict):
        raise ValueError("base_fields must be an object when present")
    if skill_routing is not None and not isinstance(skill_routing, dict):
        raise ValueError("skill_routing must be an object when present")

    return build_runtime_truth_packet(
        run_id=run_id,
        task=task,
        module_assignments=module_assignments,
        base_fields=base_fields,
        skill_routing=skill_routing,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Python-owned runtime truth packet.")
    parser.add_argument("--input-json-path", required=True)
    parser.add_argument("--output-json-path")
    args = parser.parse_args(argv)

    input_path = Path(args.input_json_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    packet = build_runtime_truth_packet_from_payload(payload)
    text = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"

    if args.output_json_path:
        Path(args.output_json_path).write_text(text, encoding="utf-8")

    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
