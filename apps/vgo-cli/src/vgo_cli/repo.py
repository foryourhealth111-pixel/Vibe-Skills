from __future__ import annotations

import json
from pathlib import Path
import sys


CONTRACTS_SRC = Path(__file__).resolve().parents[4] / 'packages' / 'contracts' / 'src'
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.installed_runtime_contract import default_installed_runtime_config, merge_installed_runtime_config


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_governance(repo_root: Path) -> dict:
    return load_json(repo_root / 'config' / 'version-governance.json')


def get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
    return merge_installed_runtime_config(load_governance(repo_root), default_installed_runtime_config())


def resolve_canonical_repo_root(start_path: Path) -> Path | None:
    current = start_path.resolve()
    while True:
        if (current / '.git').exists() and (current / 'config' / 'version-governance.json').exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
