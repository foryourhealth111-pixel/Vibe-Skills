from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_python_entrypoints_are_compatibility_shims() -> None:
    cases = [
        (
            ROOT / 'scripts' / 'install' / 'install_vgo_adapter.py',
            'vgo_installer.install_runtime',
            'def install_runtime_core(',
        ),
        (
            ROOT / 'scripts' / 'uninstall' / 'uninstall_vgo_adapter.py',
            'vgo_installer.uninstall_runtime',
            'def runtime_core_inventory(',
        ),
        (
            ROOT / 'scripts' / 'router' / 'invoke-pack-route.py',
            'vgo_cli.main',
            'def invoke_canonical_router(',
        ),
        (
            ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'router_contract.py',
            'vgo_runtime.router_contract_runtime',
            'def route_prompt(',
        ),
        (
            ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'custom_admission.py',
            'vgo_runtime.custom_admission',
            'def load_custom_admission(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'bootstrap_doctor.py',
            'vgo_verify.bootstrap_doctor',
            'def setting_value(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'release_notes_quality.py',
            'vgo_verify.release_notes_quality',
            'REQUIRED_HEADINGS =',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'coherence_gate.py',
            'vgo_verify.runtime_coherence',
            'def content_contains(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'freshness_gate.py',
            'vgo_verify.runtime_freshness',
            'def build_freshness_context(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'runtime_delivery_acceptance.py',
            'vgo_verify.runtime_delivery_acceptance',
            'def _normalize_truth_state(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'release_truth_gate.py',
            'vgo_verify.release_truth',
            'def _normalize_truth_state(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'router_ai_connectivity_probe.py',
            'vgo_verify.router_ai_connectivity_probe',
            'class ProbeContext',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'router_bridge_gate.py',
            'vgo_verify.router_bridge_gate',
            'def run_bridge(',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'opencode_preview_smoke.py',
            'vgo_verify.opencode_preview_smoke',
            'EXPECTED_FILES =',
        ),
        (
            ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'workflow_acceptance_runner.py',
            'vgo_verify.workflow_acceptance',
            'def _normalize_truth_state(',
        ),
    ]

    for path, delegated_module, forbidden_symbol in cases:
        content = path.read_text(encoding='utf-8')
        if 'scripts/verify/runtime_neutral' in str(path):
            assert '_bootstrap.py' in content, path
        assert delegated_module in content, path
        assert forbidden_symbol not in content, path
        assert len(content.splitlines()) < 80, path
