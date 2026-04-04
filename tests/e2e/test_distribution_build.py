from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSEMBLER_PATH = ROOT / 'tools' / 'build' / 'assemble_distribution.py'
BUNDLE_PATH = ROOT / 'tools' / 'release' / 'build_release_bundle.py'


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'unable to load module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_distribution_build_creates_generated_outputs(tmp_path) -> None:
    assembler = _load_module('distribution_assembler', ASSEMBLER_PATH)
    bundle_builder = _load_module('release_bundle_builder', BUNDLE_PATH)

    dist_out = tmp_path / 'dist-out'
    manifest_path = dist_out / 'manifest.json'
    bundle_path = tmp_path / 'bundle-out' / 'release-bundle.json'

    assert not manifest_path.exists()
    manifest = assembler.assemble_distribution(dist_out, host_id='codex', profile='minimal')
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert payload['generated'] is True
    assert payload['inputs']['runtime_core_manifest'].endswith('config/runtime-core-packaging.minimal.json')
    assert payload['inputs']['runtime_script_manifest'].endswith('config/runtime-script-manifest.json')
    assert payload['inputs']['runtime_config_manifest'].endswith('config/runtime-config-manifest.json')
    assert payload['inputs']['skill_catalog_owner'] == 'skill-catalog'
    assert payload['inputs']['skill_source_root'].endswith('catalog/skills')
    role_dirs = payload['runtime_payload_roles']['role_groups']['directories']
    role_files = payload['runtime_payload_roles']['role_groups']['files']
    assert 'packages/runtime-core' in role_dirs['semantic_owners']
    assert role_dirs['compatibility_shims'] == []
    assert {
        'scripts/router/runtime_neutral/router_contract.py',
        'scripts/router/runtime_neutral/custom_admission.py',
    } == set(role_files['compatibility_runtime_neutral_router_files'])
    assert {
        'scripts/verify/runtime_neutral/_bootstrap.py',
    } == set(role_files['compatibility_runtime_neutral_verification_support_files'])
    assert {
        'scripts/verify/runtime_neutral/bootstrap_doctor.py',
        'scripts/verify/runtime_neutral/coherence_gate.py',
        'scripts/verify/runtime_neutral/freshness_gate.py',
        'scripts/verify/runtime_neutral/opencode_preview_smoke.py',
        'scripts/verify/runtime_neutral/release_notes_quality.py',
        'scripts/verify/runtime_neutral/release_truth_gate.py',
        'scripts/verify/runtime_neutral/router_ai_connectivity_probe.py',
        'scripts/verify/runtime_neutral/router_bridge_gate.py',
        'scripts/verify/runtime_neutral/runtime_delivery_acceptance.py',
        'scripts/verify/runtime_neutral/workflow_acceptance_runner.py',
    } == set(role_files['compatibility_runtime_neutral_verification_files'])
    assert {
        'scripts/install/Install-VgoAdapter.ps1',
        'scripts/uninstall/Uninstall-VgoAdapter.ps1',
    } == set(role_files['compatibility_shim_files'])
    assert payload['runtime_payload_roles']['notes']['flat_projection_contract']
    config_role_groups = payload['runtime_config_payload_roles']['role_groups']
    assert payload['runtime_config_payload_roles']['source_manifest'].endswith('config/runtime-config-manifest.json')
    assert config_role_groups['directories']['managed_runtime_config_roots'] == []
    assert {
        'config/runtime-config-manifest.json',
        'config/runtime-script-manifest.json',
        'config/runtime-contract.json',
        'config/runtime-core-packaging.json',
        'config/version-governance.json',
    }.issubset(set(config_role_groups['files']['runtime_governance_files']))
    assert payload['runtime_config_payload_roles']['notes']['flat_projection_contract']
    governance_roles = payload['governance_runtime_roles']
    assert governance_roles['runtime_payload_roles']['notes']['flat_projection_contract']
    assert 'packages/runtime-core/src/vgo_runtime/router_bridge.py' in governance_roles['required_runtime_marker_groups']['semantic_owners']
    runtime_core_roles = payload['runtime_core_payload_roles']['payload_roles']
    assert runtime_core_roles['delivery_model']['bundled_skill_mode'] == 'allowlist_only_plus_canonical_vibe'
    assert (dist_out / 'catalog' / 'profiles' / 'index.json').exists()
    assert (dist_out / 'catalog' / 'skills' / 'brainstorming' / 'SKILL.md').exists()

    bundle = bundle_builder.build_release_bundle(manifest_path, tmp_path / 'bundle-out')
    assert bundle_path.exists()
    bundle_payload = json.loads(bundle_path.read_text(encoding='utf-8'))
    assert bundle_payload['generated'] is True
    assert bundle_payload['distribution_manifest'] == str(manifest_path.resolve())
    assert bundle_payload['runtime_payload_roles']['notes']['flat_projection_contract']
    assert bundle_payload['runtime_config_payload_roles']['notes']['flat_projection_contract']
    assert bundle_payload['runtime_config_payload_roles']['role_groups']['directories']['preview_host_config_roots'] == []
    assert bundle_payload['governance_runtime_roles']['required_runtime_marker_notes']['flat_projection_contract']
    assert bundle_payload['runtime_core_payload_roles']['payload_roles']['delivery_model']['bundled_skill_mode'] == 'allowlist_only_plus_canonical_vibe'
    assert bundle['host_id'] == manifest['host_id']
