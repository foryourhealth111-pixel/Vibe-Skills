from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / 'packages' / 'contracts' / 'src'
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.governance_runtime_roles import (
    derive_required_runtime_marker_projection,
    derive_runtime_payload_roles,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding='utf-8',
        newline='\n',
    )


def sync_version_governance_runtime_roles(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    governance_path = root / 'config' / 'version-governance.json'
    governance = load_json(governance_path)

    packaging = dict(governance.get('packaging') or {})
    runtime_payload = dict(packaging.get('runtime_payload') or {})
    packaging['runtime_payload_roles'] = derive_runtime_payload_roles(runtime_payload)
    governance['packaging'] = packaging

    runtime_root = dict(governance.get('runtime') or {})
    installed_runtime = dict(runtime_root.get('installed_runtime') or {})
    projection = derive_required_runtime_marker_projection(list(installed_runtime.get('required_runtime_markers') or []))
    installed_runtime['required_runtime_marker_groups'] = projection['required_runtime_marker_groups']
    installed_runtime['required_runtime_marker_notes'] = projection['required_runtime_marker_notes']
    runtime_root['installed_runtime'] = installed_runtime
    governance['runtime'] = runtime_root

    write_json(governance_path, governance)
    return {
        'schema_version': 1,
        'generated': True,
        'repo_root': str(root),
        'governance_path': str(governance_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync version-governance runtime role projections from flat runtime payload and marker owners.')
    parser.add_argument('--repo-root', default=str(REPO_ROOT))
    args = parser.parse_args()
    result = sync_version_governance_runtime_roles(args.repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
