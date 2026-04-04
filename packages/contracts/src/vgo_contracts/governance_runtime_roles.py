from __future__ import annotations

from typing import Any


RUNTIME_PAYLOAD_ROLE_NOTES = {
    "flat_projection_contract": "runtime_payload.files and runtime_payload.directories remain the compatibility projection for existing payload consumers.",
    "owner_boundary_rule": "Runtime payload root files bootstrap the installed runtime, while semantic ownership for runtime behavior stays in the CLI app and package-owned cores referenced by required_runtime_markers.",
}

REQUIRED_RUNTIME_MARKER_NOTES = {
    "flat_projection_contract": "required_runtime_markers remains the flat compatibility projection consumed by installed-runtime checks and gates.",
    "grouping_scope": "required_runtime_marker_groups classify the same marker set by responsibility; they are parity sentinels, not an exhaustive inventory of every file shipped under each package-owned directory.",
}


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").replace("\\", "/").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def derive_runtime_payload_roles(runtime_payload: dict[str, Any]) -> dict[str, Any]:
    files = _ordered_unique(list(runtime_payload.get("files") or []))
    directories = _ordered_unique(list(runtime_payload.get("directories") or []))
    return {
        "files": {
            "root_entrypoints": [path for path in files if not path.startswith("config/")],
            "governance_manifests": [path for path in files if path.startswith("config/")],
        },
        "directories": {
            "runtime_support_assets": directories,
        },
        "notes": dict(RUNTIME_PAYLOAD_ROLE_NOTES),
    }


def derive_required_runtime_marker_groups(required_runtime_markers: list[str]) -> dict[str, list[str]]:
    groups = {
        "governance_and_manifests": [],
        "semantic_owners": [],
        "runtime_entrypoints_and_support": [],
        "verification_surfaces": [],
        "router_and_compatibility_surfaces": [],
    }
    for marker in _ordered_unique(list(required_runtime_markers or [])):
        if marker == "SKILL.md" or marker.startswith("config/"):
            groups["governance_and_manifests"].append(marker)
            continue
        if marker.startswith(("apps/", "packages/")):
            groups["semantic_owners"].append(marker)
            continue
        if marker == "scripts/verify/runtime_neutral/router_bridge_gate.py":
            groups["router_and_compatibility_surfaces"].append(marker)
            continue
        if marker.startswith("scripts/verify/"):
            groups["verification_surfaces"].append(marker)
            continue
        if marker.startswith("scripts/router/"):
            groups["router_and_compatibility_surfaces"].append(marker)
            continue
        groups["runtime_entrypoints_and_support"].append(marker)
    return groups


def derive_required_runtime_marker_projection(required_runtime_markers: list[str]) -> dict[str, Any]:
    return {
        "required_runtime_marker_groups": derive_required_runtime_marker_groups(required_runtime_markers),
        "required_runtime_marker_notes": dict(REQUIRED_RUNTIME_MARKER_NOTES),
    }
