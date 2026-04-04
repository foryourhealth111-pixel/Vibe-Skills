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
