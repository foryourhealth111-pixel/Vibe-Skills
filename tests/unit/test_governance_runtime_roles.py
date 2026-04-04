from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / 'packages' / 'contracts' / 'src' / 'vgo_contracts' / 'governance_runtime_roles.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('governance_runtime_roles_unit', MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'unable to load module from {MODULE_PATH}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_payload_roles_are_derived_from_flat_payload_projection() -> None:
    module = _load_module()
    roles = module.derive_runtime_payload_roles(
        {
            'files': ['SKILL.md', 'install.sh', 'config/runtime-script-manifest.json'],
            'directories': ['templates', 'mcp'],
        }
    )

    assert roles['files']['root_entrypoints'] == ['SKILL.md', 'install.sh']
    assert roles['files']['governance_manifests'] == ['config/runtime-script-manifest.json']
    assert roles['directories']['runtime_support_assets'] == ['templates', 'mcp']
    assert roles['notes']['flat_projection_contract']


def test_required_runtime_marker_groups_classify_owners_and_compatibility_surfaces() -> None:
    module = _load_module()
    groups = module.derive_required_runtime_marker_groups(
        [
            'SKILL.md',
            'config/version-governance.json',
            'apps/vgo-cli/src/vgo_cli/main.py',
            'packages/runtime-core/src/vgo_runtime/router_bridge.py',
            'install.ps1',
            'scripts/runtime/invoke-vibe-runtime.ps1',
            'scripts/verify/vibe-installed-runtime-freshness-gate.ps1',
            'scripts/router/invoke-pack-route.py',
            'scripts/verify/runtime_neutral/router_bridge_gate.py',
        ]
    )

    assert groups['governance_and_manifests'] == ['SKILL.md', 'config/version-governance.json']
    assert groups['semantic_owners'] == [
        'apps/vgo-cli/src/vgo_cli/main.py',
        'packages/runtime-core/src/vgo_runtime/router_bridge.py',
    ]
    assert groups['runtime_entrypoints_and_support'] == ['install.ps1', 'scripts/runtime/invoke-vibe-runtime.ps1']
    assert groups['verification_surfaces'] == ['scripts/verify/vibe-installed-runtime-freshness-gate.ps1']
    assert groups['router_and_compatibility_surfaces'] == [
        'scripts/router/invoke-pack-route.py',
        'scripts/verify/runtime_neutral/router_bridge_gate.py',
    ]
