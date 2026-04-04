from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_neutral_verification_entrypoints_use_verification_core_modules() -> None:
    cases = [
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'bootstrap_doctor.py',
            'vgo_verify.bootstrap_doctor',
            'def setting_value(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'release_notes_quality.py',
            'vgo_verify.release_notes_quality',
            'REQUIRED_HEADINGS =',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'coherence_gate.py',
            'vgo_verify.runtime_coherence',
            'def content_contains(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'freshness_gate.py',
            'vgo_verify.runtime_freshness',
            'def build_freshness_context(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'runtime_delivery_acceptance.py',
            'vgo_verify.runtime_delivery_acceptance',
            'def _normalize_truth_state(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'release_truth_gate.py',
            'vgo_verify.release_truth',
            'def _normalize_truth_state(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'router_ai_connectivity_probe.py',
            'vgo_verify.router_ai_connectivity_probe',
            'class ProbeContext',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'router_bridge_gate.py',
            'vgo_verify.router_bridge_gate',
            'def run_bridge(',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'opencode_preview_smoke.py',
            'vgo_verify.opencode_preview_smoke',
            'EXPECTED_FILES =',
        ),
        (
            REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / 'workflow_acceptance_runner.py',
            'vgo_verify.workflow_acceptance',
            'def _normalize_truth_state(',
        ),
    ]

    for path, delegated_module, forbidden_symbol in cases:
        content = path.read_text(encoding='utf-8')
        assert "_bootstrap.py" in content, path
        assert 'ensure_verification_core_src_on_path()' in content, path
        assert 'packages' not in content, path
        assert delegated_module in content, path
        assert forbidden_symbol not in content, path
        assert len(content.splitlines()) < 80, path


def test_runtime_neutral_verification_shims_share_bootstrap_helper() -> None:
    helper = (REPO_ROOT / 'scripts' / 'verify' / 'runtime_neutral' / '_bootstrap.py').read_text(encoding='utf-8')

    assert 'def ensure_verification_core_src_on_path(' in helper
    assert "packages' / 'verification-core' / 'src'" in helper
    assert 'sys.path.insert(0, src_str)' in helper


def test_verification_core_uses_local_bootstrap_helper_for_contract_path_setup() -> None:
    bootstrap = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / '_bootstrap.py').read_text(encoding='utf-8')
    policies = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'policies.py').read_text(encoding='utf-8')

    assert 'def ensure_contracts_src_on_path' in bootstrap
    assert 'from ._bootstrap import ensure_contracts_src_on_path' in policies
    assert 'CONTRACTS_SRC =' not in policies


def test_verification_core_shares_repo_root_resolver() -> None:
    shared = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / '_repo.py').read_text(encoding='utf-8')
    policies = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'policies.py').read_text(encoding='utf-8')

    assert 'def resolve_repo_root(' in shared
    assert 'from ._repo import resolve_repo_root' in policies
    assert 'def resolve_repo_root(' not in policies

    for relpath in [
        'bootstrap_doctor_support.py',
        'release_notes_quality_support.py',
        'router_ai_probe_support.py',
        'router_bridge_gate_support.py',
        'runtime_delivery_acceptance_support.py',
    ]:
        content = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / relpath).read_text(encoding='utf-8')
        assert 'from ._repo import resolve_repo_root' in content
        assert 'def resolve_repo_root(' not in content


def test_verification_core_shares_io_helpers() -> None:
    shared = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / '_io.py').read_text(encoding='utf-8')

    assert 'def utc_now(' in shared
    assert 'def write_text(' in shared
    assert 'def load_json(' in shared

    policies = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'policies.py').read_text(encoding='utf-8')
    assert 'from ._io import load_json, utc_now, write_text' in policies
    assert 'def utc_now(' not in policies
    assert 'def write_text(' not in policies
    assert 'def load_json(' not in policies

    for relpath in [
        'bootstrap_doctor_support.py',
        'release_notes_quality_support.py',
        'router_ai_probe_support.py',
        'router_bridge_gate_support.py',
        'runtime_delivery_acceptance_support.py',
    ]:
        content = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / relpath).read_text(encoding='utf-8')
        assert 'from ._io import ' in content
        assert 'def utc_now(' not in content
        assert 'def write_text(' not in content

    for relpath in [
        'bootstrap_doctor_support.py',
        'router_ai_probe_support.py',
        'router_bridge_gate_support.py',
        'runtime_delivery_acceptance_support.py',
    ]:
        content = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / relpath).read_text(encoding='utf-8')
        assert 'def load_json(' not in content


def test_bootstrap_doctor_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'bootstrap_doctor.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'bootstrap_doctor_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'bootstrap_doctor_runtime.py').read_text(encoding='utf-8')

    assert 'from .bootstrap_doctor_runtime import build_bootstrap_artifact' in runtime
    assert 'from .bootstrap_doctor_support import (' in runtime

    assert 'def setting_value(' not in runtime
    assert 'def resolved_setting_state(' not in runtime
    assert 'def command_present(' not in runtime

    assert 'def setting_value(' in support
    assert 'def resolved_setting_state(' in support
    assert 'def command_present(' in support

    assert 'def build_bootstrap_artifact(' in evaluator


def test_runtime_delivery_acceptance_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_delivery_acceptance.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_delivery_acceptance_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_delivery_acceptance_runtime.py').read_text(encoding='utf-8')

    assert 'from .runtime_delivery_acceptance_runtime import evaluate_delivery_acceptance' in runtime
    assert 'from .runtime_delivery_acceptance_support import (' in runtime

    assert 'def _normalize_truth_state(' not in runtime
    assert 'def _extract_section(' not in runtime
    assert 'def _manual_spot_checks_from_requirement(' not in runtime

    assert 'def _normalize_truth_state(' in support
    assert 'def _extract_section(' in support
    assert 'def _manual_spot_checks_from_requirement(' in support

    assert 'def evaluate_delivery_acceptance(' in evaluator


def test_runtime_freshness_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_freshness.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_freshness_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'runtime_freshness_runtime.py').read_text(encoding='utf-8')

    assert 'from .runtime_freshness_runtime import evaluate_freshness_runtime' in runtime
    assert 'from .runtime_freshness_support import (' in runtime

    assert 'file_parity(' not in runtime
    assert 'relative_file_list(' not in runtime
    assert 'resolve_packaging_contract(' not in runtime
    assert 'mirror_topology_targets(' not in runtime

    assert 'def build_freshness_context(' in support
    assert 'def write_freshness_artifacts(' in support
    assert 'def write_freshness_receipt(' in support

    assert 'def evaluate_freshness_runtime(' in evaluator


def test_policies_delegate_to_contract_mirror_topology_helper() -> None:
    policies = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'policies.py').read_text(encoding='utf-8')

    assert 'resolve_mirror_topology_targets as _contract_resolve_mirror_targets' in policies
    assert 'def _mirror_topology_targets_fallback(' in policies
    assert 'def mirror_topology_targets(' in policies


def test_opencode_preview_smoke_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'opencode_preview_smoke.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'opencode_preview_smoke_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'opencode_preview_smoke_runtime.py').read_text(encoding='utf-8')

    assert 'from .opencode_preview_smoke_runtime import evaluate_opencode_preview' in runtime
    assert 'from .opencode_preview_smoke_support import (' in runtime

    assert 'def run(' not in runtime
    assert 'def write_json(' not in runtime
    assert 'def detect_skill_hit(' not in runtime
    assert 'EXPECTED_FILES = [' not in runtime

    assert 'def run(' in support
    assert 'def write_json(' in support
    assert 'def detect_skill_hit(' in support
    assert 'EXPECTED_FILES = [' in support

    assert 'def evaluate_opencode_preview(' in evaluator


def test_router_ai_connectivity_probe_delegates_probe_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_ai_connectivity_probe.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_ai_probe_support.py').read_text(encoding='utf-8')
    advice = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_ai_probe_advice.py').read_text(encoding='utf-8')
    vector = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_ai_probe_vector.py').read_text(encoding='utf-8')

    assert 'from .router_ai_probe_advice import (' in runtime
    assert 'from .router_ai_probe_support import (' in runtime
    assert 'from .router_ai_probe_vector import probe_vector_diff' in runtime

    assert 'def resolve_repo_root(' not in runtime
    assert 'def settings_env(' not in runtime
    assert 'def classify_scope(' not in runtime
    assert 'def probe_advice_connectivity(' not in runtime
    assert 'def probe_vector_diff(' not in runtime

    assert 'from ._repo import resolve_repo_root' in support


def test_release_notes_quality_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'release_notes_quality.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'release_notes_quality_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'release_notes_quality_runtime.py').read_text(encoding='utf-8')

    assert 'from .release_notes_quality_runtime import evaluate_note, evaluate_release_notes' in runtime
    assert 'from .release_notes_quality_support import (' in runtime

    assert 'REQUIRED_HEADINGS = [' not in runtime
    assert 'def load_governance(' not in runtime
    assert 'def default_release_note_path(' not in runtime

    assert 'REQUIRED_HEADINGS = [' in support
    assert 'def load_governance(' in support
    assert 'def default_release_note_path(' in support

    assert 'def evaluate_release_notes(' in evaluator
    assert 'def evaluate_note(' in evaluator


def test_router_bridge_gate_delegates_support_and_runtime_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_bridge_gate.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_bridge_gate_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'router_bridge_gate_runtime.py').read_text(encoding='utf-8')

    assert 'from .router_bridge_gate_runtime import evaluate_router_bridge, run_bridge' in runtime
    assert 'from .router_bridge_gate_support import resolve_repo_root, write_artifacts' in runtime

    assert 'def write_artifacts(' not in runtime
    assert 'def evaluate_router_bridge(' in evaluator
    assert 'def run_bridge(' in evaluator
    assert 'from .router_bridge_gate_support import load_json, utc_now' in evaluator
    assert 'def write_artifacts(' in support
    assert 'from ._io import load_json, utc_now, write_text' in support


def test_workflow_acceptance_delegates_runtime_and_support_helpers() -> None:
    runtime = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'workflow_acceptance.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'workflow_acceptance_support.py').read_text(encoding='utf-8')
    evaluator = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'workflow_acceptance_runtime.py').read_text(encoding='utf-8')

    assert 'from .workflow_acceptance_runtime import evaluate_workflow_acceptance' in runtime
    assert 'from .workflow_acceptance_support import write_artifacts' in runtime

    assert 'def write_artifacts(' not in runtime
    assert 'def evaluate_workflow_acceptance(' in evaluator
    assert 'def write_artifacts(' in support
