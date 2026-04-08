from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vgo_contracts.adapter_descriptor import AdapterDescriptor


def test_adapter_descriptor_requires_id() -> None:
    descriptor = AdapterDescriptor(
        id='codex',
        default_target_root='~/.codex',
        default_target_root_env='CODEX_HOME',
        default_target_root_kind='host-home',
    )
    assert descriptor.id == 'codex'
    assert descriptor.default_target_root == '~/.codex'
    assert descriptor.default_target_root_env == 'CODEX_HOME'
    assert descriptor.default_target_root_kind == 'host-home'


def test_adapter_descriptor_normalizes_optional_target_root_metadata() -> None:
    descriptor = AdapterDescriptor(
        id=' codex ',
        default_target_root=' ~/.codex ',
        default_target_root_env=' CODEX_HOME ',
        default_target_root_kind=' host-home ',
    )

    assert descriptor.id == 'codex'
    assert descriptor.default_target_root == '~/.codex'
    assert descriptor.default_target_root_env == 'CODEX_HOME'
    assert descriptor.default_target_root_kind == 'host-home'


def test_host_profiles_expose_discoverable_entries_as_presentational_surface() -> None:
    import json

    profiles = sorted((ROOT / 'adapters').glob('*/host-profile.json'))

    assert profiles, 'expected at least one adapter host profile'
    discoverable_profiles: list[Path] = []

    for profile_path in profiles:
        payload = json.loads(profile_path.read_text(encoding='utf-8'))
        if 'discoverable_entries' not in payload:
            continue
        discoverable_profiles.append(profile_path)
        discoverable_entries = payload['discoverable_entries']
        assert discoverable_entries['shared_source'] == 'config/vibe-entry-surfaces.json'
        assert discoverable_entries['authority_owner'] == 'vibe'
        assert discoverable_entries['presentational_only'] is True
        assert discoverable_entries['projection_mode'] == 'generated_wrapper_entries'
        assert isinstance(discoverable_entries['host_visible_surface'], str)
        assert discoverable_entries['host_visible_surface'].strip()

    assert discoverable_profiles, 'expected at least one host profile with discoverable entry surfaces'
