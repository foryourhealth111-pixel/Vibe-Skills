from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_router_entrypoint_uses_runtime_core_modules() -> None:
    bridge = (REPO_ROOT / 'scripts' / 'router' / 'invoke-pack-route.py').read_text(encoding='utf-8')
    runtime_bridge = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'runtime_bridge.py').read_text(encoding='utf-8')
    contract = (REPO_ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'router_contract.py').read_text(encoding='utf-8')
    custom = (REPO_ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'custom_admission.py').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in bridge
    assert 'from .runtime_support import resolve_repo_root' in runtime_bridge
    assert 'def resolve_repo_root(' not in runtime_bridge
    assert 'def invoke_canonical_router(' not in bridge
    assert 'def parse_args(' not in bridge

    assert 'vgo_runtime.router_contract_runtime' in contract
    assert 'def route_prompt(' not in contract

    assert 'vgo_runtime.custom_admission' in custom
    assert 'def load_custom_admission(' not in custom



def test_router_contract_runtime_keeps_candidate_audit_without_route_confirmation_surface() -> None:
    runtime = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_runtime.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'runtime_support.py').read_text(encoding='utf-8')

    assert 'from .runtime_support import (' in runtime
    assert 'from .kernel.skill_index import build_skill_catalog, build_skill_index_from_catalog' in runtime
    assert 'candidate_source": LOCAL_CANDIDATE_SOURCE' in runtime

    assert 'def resolve_repo_root(' not in runtime
    assert 'def load_json(' not in runtime
    assert 'def normalize_text(' not in runtime
    assert 'pack-manifest.json' not in runtime
    assert 'skill-keyword-index.json' not in runtime
    assert 'skill-routing-rules.json' not in runtime
    assert 'skills-lock.json' not in runtime

    assert 'def resolve_repo_root(' in support
    assert 'def load_json(' in support
    assert 'def load_router_config_bundle(' in support
    assert 'def normalize_text(' in support
    assert 'def resolve_target_root(' in support
    assert 'def read_skill_descriptor(' in support
    assert 'def build_confirm_ui(' not in runtime
    assert '"confirm_ui"' not in runtime
    assert not (REPO_ROOT / 'scripts' / 'router' / 'modules' / '46-confirm-ui.ps1').exists()
    assert not (REPO_ROOT / 'config' / 'confirm-ui-policy.json').exists()
    assert 'def build_fallback_truth(' in runtime
