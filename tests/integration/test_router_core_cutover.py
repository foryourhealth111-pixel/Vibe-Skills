from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_router_entrypoint_uses_runtime_core_modules() -> None:
    bridge = (REPO_ROOT / 'scripts' / 'router' / 'invoke-pack-route.py').read_text(encoding='utf-8')
    runtime_bridge = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_bridge.py').read_text(encoding='utf-8')
    contract = (REPO_ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'router_contract.py').read_text(encoding='utf-8')
    custom = (REPO_ROOT / 'scripts' / 'router' / 'runtime_neutral' / 'custom_admission.py').read_text(encoding='utf-8')

    assert 'vgo_cli.main' in bridge
    assert 'from .router_contract_support import resolve_repo_root' in runtime_bridge
    assert 'def resolve_repo_root(' not in runtime_bridge
    assert 'def invoke_canonical_router(' not in bridge
    assert 'def parse_args(' not in bridge

    assert 'vgo_runtime.router_contract_runtime' in contract
    assert 'def route_prompt(' not in contract

    assert 'vgo_runtime.custom_admission' in custom
    assert 'def load_custom_admission(' not in custom



def test_router_contract_runtime_delegates_selection_and_presentation_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_runtime.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_support.py').read_text(encoding='utf-8')
    selection = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_selection.py').read_text(encoding='utf-8')
    presentation = (REPO_ROOT / 'packages' / 'runtime-core' / 'src' / 'vgo_runtime' / 'router_contract_presentation.py').read_text(encoding='utf-8')

    assert 'from .router_contract_support import (' in runtime
    assert 'from .router_contract_selection import get_pack_default_candidate, select_pack_candidate' in runtime
    assert 'from .router_contract_presentation import build_confirm_ui, build_fallback_truth' in runtime
    assert 'load_router_config_bundle' in runtime

    assert 'def resolve_repo_root(' not in runtime
    assert 'def load_json(' not in runtime
    assert 'def normalize_text(' not in runtime
    assert 'def select_pack_candidate(' not in runtime
    assert 'def build_confirm_ui(' not in runtime
    assert 'def build_fallback_truth(' not in runtime
    assert 'pack-manifest.json' not in runtime
    assert 'skill-alias-map.json' not in runtime
    assert 'router-thresholds.json' not in runtime
    assert 'skill-keyword-index.json' not in runtime
    assert 'fallback-governance.json' not in runtime
    assert 'skill-routing-rules.json' not in runtime

    assert 'def resolve_repo_root(' in support
    assert 'def load_json(' in support
    assert 'def load_router_config_bundle(' in support
    assert 'def normalize_text(' in support
    assert 'def resolve_target_root(' in support
    assert 'def read_skill_descriptor(' in support

    assert 'def get_pack_default_candidate(' in selection
    assert 'def select_pack_candidate(' in selection

    assert 'def build_confirm_ui(' in presentation
    assert 'def build_fallback_truth(' in presentation
