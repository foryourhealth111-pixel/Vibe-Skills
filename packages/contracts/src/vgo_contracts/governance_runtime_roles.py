from __future__ import annotations

from typing import Any


RUNTIME_PAYLOAD_ROLE_NOTES = {
    "flat_projection_contract": "runtime_payload.files and runtime_payload.directories remain the compatibility projection for existing payload consumers.",
    "owner_boundary_rule": "The install receipt owns the installed file inventory and hashes; runtime semantics remain in the package-owned cores shipped by that receipt.",
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
