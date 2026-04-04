from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_CONFIG_RELATIVE_PATH = Path("config/distribution-manifest-sources.json")
GOVERNANCE_RELATIVE_PATH = Path("config/version-governance.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten_strings(value: object) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        if value.strip():
            items.append(value)
    elif isinstance(value, list):
        for entry in value:
            items.extend(flatten_strings(entry))
    elif isinstance(value, dict):
        for entry in value.values():
            items.extend(flatten_strings(entry))
    return items


def insert_after(payload: dict[str, Any], after_key: str, new_key: str, new_value: Any) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    inserted = False
    for key, value in payload.items():
        projected[key] = value
        if key == after_key:
            projected[new_key] = new_value
            inserted = True
    if not inserted:
        projected[new_key] = new_value
    return projected


def derive_lane_surface_roles(payload: dict[str, Any]) -> dict[str, Any]:
    docs = payload.get("docs") or {}
    support = payload.get("support") or {}
    proof_surfaces: list[str] = []
    proof_surfaces.extend(flatten_strings(docs))
    for key in ("platform_support", "host_support"):
        entry = support.get(key) or {}
        truth = entry.get("truth_source")
        if isinstance(truth, str) and truth.strip():
            proof_surfaces.append(truth)
    for promise in payload.get("capability_promises") or []:
        proof_surfaces.extend(flatten_strings((promise or {}).get("evidence_paths")))

    entrypoints = [
        value
        for value in (payload.get("entrypoints") or {}).values()
        if isinstance(value, str) and value.strip()
    ]

    return {
        "notes": {
            "flat_projection_contract": True,
            "projection_scope": "release_lane_manifest",
        },
        "runtime_authority": dict(payload.get("runtime_ownership") or {}),
        "repo_provided_entrypoints": ordered_unique(entrypoints),
        "proof_surfaces": ordered_unique(proof_surfaces),
        "boundary_claims": list(payload.get("non_goals") or []),
    }


def derive_public_surface_roles(payload: dict[str, Any]) -> dict[str, Any]:
    install_entrypoints = payload.get("install_entrypoints") or {}
    repo_install_surfaces: list[str] = []
    for key, value in install_entrypoints.items():
        if key in {"host_managed", "notes"}:
            continue
        repo_install_surfaces.extend(flatten_strings(value))

    payload_surfaces: list[str] = []
    for value in (payload.get("delivers") or {}).values():
        payload_surfaces.extend(flatten_strings(value))

    reference_surfaces: list[str] = []
    entry_manifest = payload.get("entry_manifest")
    if isinstance(entry_manifest, str) and entry_manifest.strip():
        reference_surfaces.append(entry_manifest)

    host_managed = payload.get("host_managed_surfaces")
    if host_managed is None:
        host_managed = install_entrypoints.get("host_managed") or []

    return {
        "notes": {
            "flat_projection_contract": True,
            "projection_scope": "public_distribution_manifest",
        },
        "runtime_authority": {
            "runtime_role": str(payload.get("runtime_role") or ""),
            "status": str(payload.get("status") or ""),
            "host_adapter_ref": payload.get("host_adapter_ref"),
        },
        "truth_surfaces": list(payload.get("truth_sources") or []),
        "repo_provided_install_surfaces": ordered_unique(repo_install_surfaces),
        "repo_provided_payload_surfaces": ordered_unique(payload_surfaces),
        "repo_provided_reference_surfaces": ordered_unique(reference_surfaces),
        "host_managed_surfaces": list(host_managed or []),
        "boundary_claims": list(payload.get("anti_overclaim") or []),
    }


def build_dist_release_manifests(repo_root: Path | str) -> dict[str, dict[str, Any]]:
    root = Path(repo_root).resolve()
    source_config = load_json(root / SOURCE_CONFIG_RELATIVE_PATH)
    governance = load_json(root / GOVERNANCE_RELATIVE_PATH)
    release = {
        "version": str(((governance.get("release") or {}).get("version") or "")),
        "updated": str(((governance.get("release") or {}).get("updated") or "")),
    }

    manifests: dict[str, dict[str, Any]] = {}

    for item in source_config.get("lane_manifests") or []:
        output_path = str(item["output_path"])
        payload = dict(item["payload"])
        payload = insert_after(payload, "stability", "source_release", release)
        payload = insert_after(payload, "runtime_ownership", "surface_roles", derive_lane_surface_roles(payload))
        manifests[output_path] = payload

    for item in source_config.get("public_manifests") or []:
        output_path = str(item["output_path"])
        payload = dict(item["payload"])
        payload = insert_after(payload, "runtime_role", "surface_roles", derive_public_surface_roles(payload))
        payload = insert_after(payload, "summary", "source_release", release)
        manifests[output_path] = payload

    return manifests


def sync_dist_release_manifests(repo_root: Path | str, *, output_root: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    target_root = root if output_root is None else Path(output_root).resolve()
    manifests = build_dist_release_manifests(root)

    for relative_path, payload in manifests.items():
        write_json(target_root / relative_path, payload)

    return {
        "schema_version": 1,
        "generated": True,
        "repo_root": str(root),
        "output_root": str(target_root),
        "source_config": str((root / SOURCE_CONFIG_RELATIVE_PATH).resolve()),
        "governance_path": str((root / GOVERNANCE_RELATIVE_PATH).resolve()),
        "generated_outputs": list(manifests.keys()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release-facing dist manifests from authoritative source config.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default="")
    args = parser.parse_args()

    output_root = args.output_root or None
    result = sync_dist_release_manifests(args.repo_root, output_root=output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
