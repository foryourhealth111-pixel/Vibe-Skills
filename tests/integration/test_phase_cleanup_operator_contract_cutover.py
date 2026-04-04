from pathlib import Path
import json


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_phase_cleanup_operator_contract_is_policy_backed() -> None:
    policy = json.loads((REPO_ROOT / 'config' / 'phase-cleanup-policy.json').read_text(encoding='utf-8'))
    phase_cleanup = (REPO_ROOT / 'scripts' / 'governance' / 'phase-end-cleanup.ps1').read_text(encoding='utf-8')
    gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-document-asset-safety-gate.ps1').read_text(encoding='utf-8')

    assert policy['operator_contract']['preview_only_supported'] is True
    assert policy['operator_contract']['preview_only_switch'] == 'PreviewOnly'
    assert policy['operator_contract']['protected_tmp_default_action'] == 'quarantine_only'
    assert policy['operator_contract']['quarantine_handler'] == 'Move-VgoProtectedDocumentsToQuarantine'
    assert 'operator_contract = [pscustomobject]' in phase_cleanup
    assert '$cleanupRaw =' not in gate
    assert 'policy.operator_contract.preview_only_supported' in gate
    assert 'policy.operator_contract.quarantine_handler' in gate
