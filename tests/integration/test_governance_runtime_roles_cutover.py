from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_distribution_builder_uses_shared_governance_runtime_role_derivation() -> None:
    content = (REPO_ROOT / 'tools' / 'build' / 'assemble_distribution.py').read_text(encoding='utf-8')

    assert 'vgo_contracts.governance_runtime_roles' in content
    assert "governance_packaging.get('runtime_payload_roles')" not in content
    assert "governance_runtime.get('required_runtime_marker_groups')" not in content
