from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'runtime_packaging.py'
CODEX_VIBE_WRAPPER_SKILLS = [
    'vibe-do-it',
    'vibe-how-do-we-do',
    'vibe-what-do-i-want',
]


def _load_module():
    spec = importlib.util.spec_from_file_location('runtime_packaging_unit', MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'unable to load module from {MODULE_PATH}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_packaging_resolver_loads_profile_projection_from_authoritative_base() -> None:
    module = _load_module()
    minimal = module.resolve_runtime_core_packaging(REPO_ROOT, 'minimal')
    full = module.resolve_runtime_core_packaging(REPO_ROOT, 'full')

    assert minimal['profile'] == 'minimal'
    assert full['profile'] == 'full'
    assert minimal['copy_bundled_skills'] is False
    assert full['copy_bundled_skills'] is True
    assert minimal['payload_roles']['delivery_model']['bundled_skill_mode'] == 'hidden_allowlist_internal_corpus_plus_canonical_vibe'
    assert full['payload_roles']['delivery_model']['bundled_skill_mode'] == 'hidden_full_internal_corpus_minus_canonical_vibe'
    assert minimal['compatibility_skill_projections']['projected_skill_names'] == []
    assert sorted(full['compatibility_skill_projections']['projected_skill_names']) == CODEX_VIBE_WRAPPER_SKILLS
    assert minimal['public_skill_surface']['mode'] == 'discoverable_wrapper_projection'
    assert full['public_skill_surface']['mode'] == 'discoverable_wrapper_projection'
    assert minimal['public_skill_surface']['discoverable_entry_surface'] == 'config/vibe-entry-surfaces.json'
    assert full['public_skill_surface']['discoverable_entry_surface'] == 'config/vibe-entry-surfaces.json'
    assert minimal['public_skill_surface']['projected_skill_names'] == ['vibe', 'vibe-want', 'vibe-how', 'vibe-do']
    assert full['public_skill_surface']['projected_skill_names'] == ['vibe', 'vibe-want', 'vibe-how', 'vibe-do']
