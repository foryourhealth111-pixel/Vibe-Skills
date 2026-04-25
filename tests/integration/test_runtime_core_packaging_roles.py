from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.json"
MINIMAL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.minimal.json"
FULL_MANIFEST = REPO_ROOT / "config" / "runtime-core-packaging.full.json"
MODULE_PATH = REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'runtime_packaging.py'
def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_runtime_packaging_module():
    spec = importlib.util.spec_from_file_location('runtime_packaging_contract', MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'unable to load module from {MODULE_PATH}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _flatten_entry_groups(groups: dict[str, list[dict]]) -> list[tuple]:
    items: list[tuple] = []
    for values in groups.values():
        for value in values:
            items.append(tuple(sorted(value.items())))
    return items


def _supports_surface_split(manifest: dict) -> bool:
    required = {
        'public_skill_surface',
        'internal_skill_corpus',
        'compatibility_skill_projections',
    }
    return required.issubset(set(manifest))


def _resolve_canonical_vibe_target(surface: dict) -> str | None:
    if not isinstance(surface, dict):
        return None
    for key in ('canonical_vibe_target_relpath', 'canonical_entrypoint_relpath'):
        value = surface.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def test_base_runtime_core_packaging_owns_shared_fields_and_profile_overlays() -> None:
    payload = _load(BASE_MANIFEST)
    roles = payload['payload_roles']

    assert payload['default_profile'] == 'full'
    assert set(payload['profiles']) == {'minimal', 'full'}
    assert 'copy_directories' not in payload
    assert set(payload['directories']) == {'skills', 'commands', 'config'}

    target_dirs = []
    for values in roles['target_directories'].values():
        target_dirs.extend(values)
    assert set(target_dirs) == set(payload['directories'])
    assert len(target_dirs) == len(set(target_dirs))

    grouped_copy_files = _flatten_entry_groups(roles['copy_files'])
    assert set(grouped_copy_files) == {tuple(sorted(item.items())) for item in payload['copy_files']}
    assert roles['notes']['flat_projection_contract']
    assert payload['profiles']['minimal']['payload_roles']['delivery_model']['compatibility_skill_projections'] == []
    assert payload['profiles']['full']['payload_roles']['delivery_model']['compatibility_skill_projections'] == []


def test_profile_runtime_core_packaging_projections_match_base_overlay_resolution() -> None:
    runtime_packaging = _load_runtime_packaging_module()
    minimal_projection = _load(MINIMAL_MANIFEST)
    full_projection = _load(FULL_MANIFEST)

    resolved_minimal = runtime_packaging.resolve_runtime_core_packaging(REPO_ROOT, 'minimal')
    resolved_full = runtime_packaging.resolve_runtime_core_packaging(REPO_ROOT, 'full')

    if _supports_surface_split(resolved_full):
        assert resolved_minimal['profile'] == 'minimal'
        assert resolved_full['profile'] == 'full'
        assert _resolve_canonical_vibe_target(resolved_minimal['public_skill_surface']) == 'skills/vibe'
        assert _resolve_canonical_vibe_target(resolved_full['public_skill_surface']) == 'skills/vibe'
        assert resolved_minimal['internal_skill_corpus']['target_relpath'].startswith('skills/vibe/')
        assert resolved_full['internal_skill_corpus']['target_relpath'].startswith('skills/vibe/')
        assert resolved_minimal['copy_directories'] == minimal_projection['copy_directories']
        assert any(
            entry.get('source') == 'commands' and entry.get('target') == 'commands'
            for entry in resolved_full['copy_directories']
            if isinstance(entry, dict)
        )
        assert not any(
            entry.get('source') == 'bundled/skills' and entry.get('target') == 'skills'
            for entry in resolved_full['copy_directories']
            if isinstance(entry, dict)
        )
    else:
        assert minimal_projection == resolved_minimal
        assert full_projection == resolved_full


def test_committed_profile_runtime_core_packaging_does_not_embed_repo_root() -> None:
    assert "_repo_root" not in _load(MINIMAL_MANIFEST)
    assert "_repo_root" not in _load(FULL_MANIFEST)


def test_profile_runtime_core_packaging_roles_describe_delivery_model() -> None:
    minimal = _load(MINIMAL_MANIFEST)
    full = _load(FULL_MANIFEST)

    if _supports_surface_split(minimal):
        assert minimal['payload_roles']['delivery_model']['bundled_skill_mode'] == 'hidden_allowlist_internal_corpus_plus_canonical_vibe'
    else:
        assert minimal['payload_roles']['delivery_model']['bundled_skill_mode'] == 'allowlist_only_plus_canonical_vibe'
    if _supports_surface_split(full):
        assert full['payload_roles']['delivery_model']['bundled_skill_mode'] == 'hidden_full_internal_corpus_minus_canonical_vibe'
    else:
        assert full['payload_roles']['delivery_model']['bundled_skill_mode'] == 'full_bundled_surface_minus_canonical_vibe'
    assert minimal['payload_roles']['delivery_model']['canonical_vibe_target_relpath'] == 'skills/vibe'
    assert full['payload_roles']['delivery_model']['canonical_vibe_target_relpath'] == 'skills/vibe'
    assert sorted(minimal['payload_roles']['delivery_model']['skills_allowlist']) == sorted(minimal['skills_allowlist'])
    assert full['payload_roles']['delivery_model']['skills_allowlist'] == []
    if _supports_surface_split(minimal):
        assert minimal['compatibility_skill_projections']['projected_skill_names'] == []
        assert minimal['internal_skill_corpus']['target_relpath'] == 'skills/vibe/bundled/skills'
        assert minimal['public_skill_surface']['mode'] == 'discoverable_wrapper_projection'
        assert minimal['public_skill_surface']['discoverable_entry_surface'] == 'config/vibe-entry-surfaces.json'
        assert minimal['public_skill_surface']['projected_skill_names'] == ['vibe', 'vibe-upgrade']
    if _supports_surface_split(full):
        assert full['compatibility_skill_projections']['projected_skill_names'] == []
        assert full['internal_skill_corpus']['entrypoint_filename'] == 'SKILL.runtime-mirror.md'
        assert full['public_skill_surface']['mode'] == 'discoverable_wrapper_projection'
        assert full['public_skill_surface']['discoverable_entry_surface'] == 'config/vibe-entry-surfaces.json'
        assert full['public_skill_surface']['projected_skill_names'] == ['vibe', 'vibe-upgrade']


def test_profile_runtime_core_packaging_role_sources_match_copy_projection() -> None:
    minimal = _load(MINIMAL_MANIFEST)
    full = _load(FULL_MANIFEST)

    minimal_sources = {tuple(sorted(item.items())) for item in minimal['payload_roles']['copy_directories']['active_sources']}
    full_sources = {tuple(sorted(item.items())) for item in full['payload_roles']['copy_directories']['active_sources']}

    assert minimal_sources == {tuple(sorted(item.items())) for item in minimal['copy_directories']}
    assert full_sources == {tuple(sorted(item.items())) for item in full['copy_directories']}
    assert all(dict(entry)['source'] == 'commands' for entry in minimal_sources)
    if _supports_surface_split(full):
        assert not any(
            dict(entry).get('source') == 'bundled/skills' and dict(entry).get('target') == 'skills'
            for entry in full_sources
        )
    else:
        assert any(dict(entry)['source'] == 'bundled/skills' for entry in full_sources)


def test_profile_managed_skill_inventory_is_manifest_owned() -> None:
    minimal = _load(MINIMAL_MANIFEST)
    full = _load(FULL_MANIFEST)

    minimal_inventory = minimal['managed_skill_inventory']
    full_inventory = full['managed_skill_inventory']

    minimal_required_runtime = set(minimal_inventory['required_runtime_skills'])
    minimal_required_workflow = set(minimal_inventory['required_workflow_skills'])
    full_required_runtime = set(full_inventory['required_runtime_skills'])
    full_required_workflow = set(full_inventory['required_workflow_skills'])
    full_optional_workflow = set(full_inventory['optional_workflow_skills'])

    assert 'vibe' in minimal_required_runtime
    assert minimal_required_runtime == full_required_runtime
    assert minimal_required_workflow == full_required_workflow
    assert full_optional_workflow == {'requesting-code-review', 'receiving-code-review', 'verification-before-completion'}
    assert not (minimal_required_runtime & minimal_required_workflow)
    assert not (full_required_runtime & full_optional_workflow)
    assert not (full_required_workflow & full_optional_workflow)
    assert sorted((minimal_required_runtime - {'vibe'}) | minimal_required_workflow) == sorted(minimal['skills_allowlist'])


def test_surface_split_semantics_are_declared_when_available() -> None:
    base = _load(BASE_MANIFEST)
    full = _load(FULL_MANIFEST)
    required = {
        'public_skill_surface',
        'internal_skill_corpus',
        'compatibility_skill_projections',
    }
    if not required.issubset(set(base)) and not required.issubset(set(full)):
        pytest.skip('surface split semantics are not available in this branch yet')

    container = full if required.issubset(set(full)) else base
    assert required.issubset(set(container))
    assert isinstance(container['public_skill_surface'], (dict, list))
    assert isinstance(container['internal_skill_corpus'], (dict, list))
    assert isinstance(container['compatibility_skill_projections'], (dict, list))

    serialized_public = json.dumps(container['public_skill_surface'], ensure_ascii=True)
    serialized_internal = json.dumps(container['internal_skill_corpus'], ensure_ascii=True)
    assert 'skills/vibe' in serialized_public or 'skills/vibe' in serialized_internal


def test_full_profile_defaults_to_no_top_level_bundled_skill_fanout_when_split_semantics_available() -> None:
    full = _load(FULL_MANIFEST)
    if not _supports_surface_split(full):
        pytest.skip('full profile still uses legacy top-level bundled skill projection')

    legacy_flatten = any(
        entry.get('source') == 'bundled/skills' and entry.get('target') == 'skills'
        for entry in full.get('copy_directories') or []
        if isinstance(entry, dict)
    )
    assert not legacy_flatten
