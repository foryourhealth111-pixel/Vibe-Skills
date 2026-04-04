from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_phase_cleanup_policy_contract_declares_preview_and_quarantine_operator_capabilities() -> None:
    policy = json.loads((REPO_ROOT / 'config' / 'phase-cleanup-policy.json').read_text(encoding='utf-8'))
    contract = policy['operator_contract']

    assert contract['preview_only_supported'] is True
    assert contract['preview_only_switch'] == 'PreviewOnly'
    assert contract['protected_tmp_default_action'] == 'quarantine_only'
    assert contract['protected_tmp_quarantine_required'] is True
    assert contract['quarantine_handler'] == 'Move-VgoProtectedDocumentsToQuarantine'


def test_document_cleanup_scenarios_keep_source_trees_for_gate_execution() -> None:
    fixtures_root = REPO_ROOT / 'scripts' / 'verify' / 'fixtures' / 'document-cleanup-safety'
    scenario_dirs = sorted(path for path in fixtures_root.iterdir() if path.is_dir())

    assert len(scenario_dirs) >= 3

    for scenario_dir in scenario_dirs:
        assert (scenario_dir / 'metadata.json').exists(), scenario_dir.name
        source_root = scenario_dir / 'source'
        assert source_root.exists() and source_root.is_dir(), scenario_dir.name
        assert any(path.is_file() for path in source_root.rglob('*')), scenario_dir.name


def test_document_cleanup_fixture_metadata_matches_fixture_contents() -> None:
    policy = json.loads((REPO_ROOT / 'config' / 'phase-cleanup-policy.json').read_text(encoding='utf-8'))
    protected_extensions = {str(ext).lower() for ext in policy['protected_document_policy']['extensions']}
    fixtures_root = REPO_ROOT / 'scripts' / 'verify' / 'fixtures' / 'document-cleanup-safety'

    for scenario_dir in sorted(path for path in fixtures_root.iterdir() if path.is_dir()):
        metadata = json.loads((scenario_dir / 'metadata.json').read_text(encoding='utf-8'))
        source_root = scenario_dir / 'source'
        tmp_root = source_root / '.tmp'

        tmp_protected = sum(
            1
            for path in tmp_root.rglob('*')
            if path.is_file() and path.suffix.lower() in protected_extensions
        )
        retained_protected = sum(
            1
            for path in source_root.rglob('*')
            if path.is_file() and path.suffix.lower() in protected_extensions and tmp_root not in path.parents
        )

        assert metadata['expected_tmp_protected'] == tmp_protected, scenario_dir.name
        assert metadata['expected_retained_outside_tmp'] == retained_protected, scenario_dir.name
        assert metadata['expected_quarantined'] == tmp_protected, scenario_dir.name
