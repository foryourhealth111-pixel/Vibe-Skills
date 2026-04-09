from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router import load_allowed_vibe_entry_ids, route_runtime_task


def test_runtime_router_allowed_entry_ids_match_shared_surface_contract() -> None:
    payload = json.loads((ROOT / 'config' / 'vibe-entry-surfaces.json').read_text(encoding='utf-8'))
    expected = frozenset(
        str(entry['id']).strip()
        for entry in payload['entries']
        if str(entry.get('id') or '').strip()
    )

    assert load_allowed_vibe_entry_ids() == expected


def test_runtime_router_rejects_entries_outside_shared_surface_contract() -> None:
    try:
        route_runtime_task('plan this change', requested_skill='vibe-xl')
    except ValueError:
        assert True
    else:
        raise AssertionError('expected unsupported entry id failure')
