import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_cut_apply_gate_inventory_is_contract_backed() -> None:
    contract = json.loads((REPO_ROOT / 'config' / 'operator-preview-contract.json').read_text(encoding='utf-8'))
    release_cut = (REPO_ROOT / 'scripts' / 'governance' / 'release-cut.ps1').read_text(encoding='utf-8')
    truth_gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-release-truth-consistency-gate.ps1').read_text(encoding='utf-8')
    train_gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-release-train-v2-gate.ps1').read_text(encoding='utf-8')

    apply_gates = contract['operators']['release-cut']['apply_gates']
    assert 'scripts/verify/vibe-release-train-v2-gate.ps1' in apply_gates
    assert 'scripts/verify/vibe-release-truth-consistency-gate.ps1' in apply_gates
    assert 'Get-ReleaseGateScriptsFromContract' in release_cut
    assert 'Get-ReleasePostcheckScriptsFromContract' in release_cut
    assert 'releaseCutOperator.apply_gates' in truth_gate
    assert 'postcheck_gates' in release_cut
    assert 'config/operator-preview-contract.json' in train_gate
    assert 'apply_gates' in train_gate


def test_release_closure_gates_consume_contract_backed_apply_inventory() -> None:
    contract = json.loads((REPO_ROOT / 'config' / 'operator-preview-contract.json').read_text(encoding='utf-8'))
    wave64_gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-wave64-82-closure-gate.ps1').read_text(encoding='utf-8')
    wave83_gate = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-wave83-100-closure-gate.ps1').read_text(encoding='utf-8')
    helpers = (REPO_ROOT / 'scripts' / 'common' / 'vibe-governance-helpers.ps1').read_text(encoding='utf-8')

    apply_gates = contract['operators']['release-cut']['apply_gates']
    assert 'scripts/verify/vibe-memory-runtime-v3-gate.ps1' in apply_gates
    assert 'scripts/verify/vibe-wave64-82-closure-gate.ps1' in apply_gates
    assert 'scripts/verify/vibe-ops-dashboard-gate.ps1' in apply_gates
    assert 'scripts/verify/vibe-wave83-100-closure-gate.ps1' in apply_gates

    assert 'function Get-VgoOperatorPreviewStringListProperty' in helpers
    assert "Get-VgoOperatorPreviewStringListProperty -RepoRoot $repoRoot -OperatorId 'release-cut' -PropertyName 'apply_gates'" in wave64_gate
    assert "Get-VgoOperatorPreviewStringListProperty -RepoRoot $repoRoot -OperatorId 'release-cut' -PropertyName 'apply_gates'" in wave83_gate
    assert 'release-cut contract preserves wave63-to-wave64 gate boundary' in wave83_gate
