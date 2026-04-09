from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.adapter_registry_support import (
    load_adapter_registry,
    normalize_adapter_host_id,
    resolve_adapter_entry,
    resolve_adapter_registry_path,
)


def test_resolve_adapter_registry_path_finds_checked_in_registry() -> None:
    path = resolve_adapter_registry_path(ROOT)
    assert path == ROOT / 'adapters' / 'index.json' or path == ROOT / 'config' / 'adapter-registry.json'


def test_normalize_adapter_host_id_supports_aliases() -> None:
    registry = load_adapter_registry(ROOT)
    assert normalize_adapter_host_id('claude', registry) == 'claude-code'
    assert normalize_adapter_host_id('codex', registry) == 'codex'


def test_resolve_adapter_entry_returns_raw_registry_entry() -> None:
    registry = load_adapter_registry(ROOT)
    entry = resolve_adapter_entry(registry, 'windsurf')
    assert entry['id'] == 'windsurf'
    assert entry['default_target_root']['rel'] == '.codeium/windsurf'
    assert entry['default_target_root']['kind'] == 'host-home'


def test_adapter_registry_exposes_shared_discoverable_vibe_entry_surface() -> None:
    registry = load_adapter_registry(ROOT)

    assert registry['discoverable_entry_surface'] == 'config/vibe-entry-surfaces.json'
    for entry in registry['adapters']:
        assert entry['discoverable_entries']['shared_source'] == registry['discoverable_entry_surface']
        assert entry['discoverable_entries']['authority_owner'] == 'vibe'
        assert entry['discoverable_entries']['projection_mode'] == 'generated_wrapper_entries'
        assert str(entry['discoverable_entries']['host_visible_surface']).strip()
