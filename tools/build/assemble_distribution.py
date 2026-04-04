from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel in (
    'packages/contracts/src',
    'packages/adapter-sdk/src',
    'packages/skill-catalog/src',
    'packages/installer-core/src',
):
    src = REPO_ROOT / rel
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_adapters.descriptor_loader import load_descriptor
from vgo_catalog.exporter import export_catalog_descriptor
from vgo_contracts.governance_runtime_roles import (
    derive_required_runtime_marker_projection,
    derive_runtime_payload_roles,
)
from vgo_installer.runtime_packaging import resolve_runtime_core_projection_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def resolve_runtime_manifest_path(profile: str) -> Path:
    return resolve_runtime_core_projection_path(REPO_ROOT, profile)


def assemble_distribution(output_dir: Path | str, *, host_id: str, profile: str = 'full') -> dict[str, Any]:
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    runtime_manifest_path = resolve_runtime_manifest_path(profile)
    runtime_manifest = load_json(runtime_manifest_path)
    runtime_payload_roles = dict(runtime_manifest.get('payload_roles') or {})
    runtime_script_manifest_path = (REPO_ROOT / 'config' / 'runtime-script-manifest.json').resolve()
    runtime_script_manifest = load_json(runtime_script_manifest_path)
    runtime_role_groups = dict(runtime_script_manifest.get('role_groups') or {})
    runtime_notes = dict(runtime_script_manifest.get('notes') or {})
    runtime_config_manifest_path = (REPO_ROOT / 'config' / 'runtime-config-manifest.json').resolve()
    runtime_config_manifest = load_json(runtime_config_manifest_path)
    runtime_config_role_groups = dict(runtime_config_manifest.get('role_groups') or {})
    runtime_config_notes = dict(runtime_config_manifest.get('notes') or {})
    governance_path = (REPO_ROOT / 'config' / 'version-governance.json').resolve()
    governance = load_json(governance_path)
    governance_packaging = dict(governance.get('packaging') or {})
    governance_runtime = dict((governance.get('runtime') or {}).get('installed_runtime') or {})
    governance_payload_roles = derive_runtime_payload_roles(dict(governance_packaging.get('runtime_payload') or {}))
    governance_marker_projection = derive_required_runtime_marker_projection(list(governance_runtime.get('required_runtime_markers') or []))
    governance_marker_groups = dict(governance_marker_projection['required_runtime_marker_groups'])
    governance_marker_notes = dict(governance_marker_projection['required_runtime_marker_notes'])
    adapter_descriptor = load_descriptor(host_id)
    catalog_descriptor = export_catalog_descriptor(target_dir)

    manifest = {
        'schema_version': 1,
        'generated': True,
        'host_id': host_id,
        'profile': profile,
        'inputs': {
            'runtime_core_manifest': str(runtime_manifest_path),
            'runtime_core_package_id': str(runtime_manifest.get('package_id') or ''),
            'runtime_script_manifest': str(runtime_script_manifest_path),
            'runtime_config_manifest': str(runtime_config_manifest_path),
            'adapter_id': adapter_descriptor.id,
            'adapter_default_target_root': adapter_descriptor.default_target_root,
            'skill_catalog_owner': str(catalog_descriptor.get('owner') or ''),
            'skill_catalog_root': str(catalog_descriptor.get('catalog_root') or ''),
            'profiles_manifest': str(catalog_descriptor.get('profiles_manifest') or ''),
            'groups_manifest': str(catalog_descriptor.get('groups_manifest') or ''),
            'metadata_manifest': str(catalog_descriptor.get('metadata_manifest') or ''),
            'skill_source_root': str(catalog_descriptor.get('skill_source_root') or ''),
        },
        'runtime_payload_roles': {
            'source_manifest': str(runtime_script_manifest_path),
            'role_groups': runtime_role_groups,
            'notes': runtime_notes,
        },
        'runtime_config_payload_roles': {
            'source_manifest': str(runtime_config_manifest_path),
            'role_groups': runtime_config_role_groups,
            'notes': runtime_config_notes,
        },
        'runtime_core_payload_roles': {
            'source_manifest': str(runtime_manifest_path),
            'payload_roles': runtime_payload_roles,
        },
        'governance_runtime_roles': {
            'source_governance': str(governance_path),
            'runtime_payload_roles': governance_payload_roles,
            'required_runtime_marker_groups': governance_marker_groups,
            'required_runtime_marker_notes': governance_marker_notes,
        },
        'artifacts': {
            'catalog_descriptor_path': str((target_dir / 'catalog' / 'metadata' / 'index.json').resolve()),
            'output_root': str(target_dir),
        },
        'ownership': {
            'semantic_owner': 'tools/build/assemble_distribution.py',
            'generated_outputs_only': True,
        },
    }
    write_json(target_dir / 'manifest.json', manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description='Assemble a generated distribution manifest from package owners.')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--host', default='codex')
    parser.add_argument('--profile', default='full')
    args = parser.parse_args()
    manifest = assemble_distribution(args.output_dir, host_id=args.host, profile=args.profile)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
