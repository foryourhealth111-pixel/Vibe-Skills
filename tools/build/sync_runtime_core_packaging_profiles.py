from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER_CORE_SRC = REPO_ROOT / 'packages' / 'installer-core' / 'src'
CONTRACTS_SRC = REPO_ROOT / 'packages' / 'contracts' / 'src'
for src in (INSTALLER_CORE_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.runtime_packaging import load_runtime_core_packaging_base, resolve_runtime_core_packaging


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def sync_runtime_core_packaging_profiles(repo_root: Path | str) -> dict[str, str]:
    root = Path(repo_root).resolve()
    base = load_runtime_core_packaging_base(root)
    manifest_map = base.get('profile_manifests') or {}
    updated: dict[str, str] = {}
    for profile, rel in manifest_map.items():
        payload = resolve_runtime_core_packaging(root, profile)
        payload.pop('profiles', None)
        payload.pop('default_profile', None)
        target_path = (root / str(rel)).resolve()
        write_json(target_path, payload)
        updated[profile] = str(target_path)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync generated runtime-core profile packaging projections from the base manifest.')
    parser.add_argument('--repo-root', default=str(REPO_ROOT))
    args = parser.parse_args()
    updated = sync_runtime_core_packaging_profiles(args.repo_root)
    print(json.dumps({'updated': updated}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
