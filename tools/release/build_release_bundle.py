from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def build_release_bundle(distribution_manifest_path: Path | str, output_dir: Path | str) -> dict[str, Any]:
    manifest_path = Path(distribution_manifest_path).resolve()
    output_root = Path(output_dir).resolve()
    distribution_manifest = load_json(manifest_path)
    bundle = {
        'schema_version': 1,
        'generated': True,
        'host_id': str(distribution_manifest.get('host_id') or ''),
        'profile': str(distribution_manifest.get('profile') or ''),
        'distribution_manifest': str(manifest_path),
        'inputs': dict(distribution_manifest.get('inputs') or {}),
        'runtime_payload_roles': dict(distribution_manifest.get('runtime_payload_roles') or {}),
        'runtime_config_payload_roles': dict(distribution_manifest.get('runtime_config_payload_roles') or {}),
        'runtime_core_payload_roles': dict(distribution_manifest.get('runtime_core_payload_roles') or {}),
        'governance_runtime_roles': dict(distribution_manifest.get('governance_runtime_roles') or {}),
        'ownership': {
            'semantic_owner': 'tools/release/build_release_bundle.py',
            'generated_outputs_only': True,
        },
    }
    write_json(output_root / 'release-bundle.json', bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a release bundle from a generated distribution manifest.')
    parser.add_argument('--distribution-manifest', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    bundle = build_release_bundle(args.distribution_manifest, args.output_dir)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
