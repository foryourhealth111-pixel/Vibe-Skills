from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vgo_cli_uses_installer_core_modules() -> None:
    main_content = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'main.py').read_text(encoding='utf-8')
    commands_content = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'commands.py').read_text(encoding='utf-8')
    core_bridge = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'core_bridge.py').read_text(encoding='utf-8')

    assert 'from .commands import install_command, passthrough_command, route_command, runtime_command, uninstall_command, verify_command' in main_content
    assert 'from .core_bridge import run_installer_core, run_router_core, run_uninstaller_core' in commands_content
    assert 'vgo_installer.install_runtime' in core_bridge
    assert 'vgo_installer.uninstall_runtime' in core_bridge
    assert 'scripts/install/install_vgo_adapter.py' not in main_content
    assert 'scripts/install/install_vgo_adapter.py' not in commands_content
    assert 'scripts/uninstall/uninstall_vgo_adapter.py' not in main_content
    assert 'scripts/uninstall/uninstall_vgo_adapter.py' not in commands_content


def test_vgo_cli_install_support_uses_specific_installer_bridge_instead_of_package_root() -> None:
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    installer_bridge = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'installer_bridge.py').read_text(encoding='utf-8')

    assert 'from .installer_bridge import refresh_install_ledger_payload' in install_support
    assert 'from vgo_installer.ledger_service import refresh_install_ledger' in installer_bridge
    assert 'from vgo_installer import refresh_install_ledger' not in installer_bridge


def test_installer_core_test_surfaces_use_specific_installer_modules_instead_of_package_root() -> None:
    content = (REPO_ROOT / 'tests' / 'unit' / 'test_materializer_runtime_noise.py').read_text(encoding='utf-8')

    assert 'from vgo_installer.materializer import copy_dir_replace, copy_skill_roots_without_self_shadow' in content
    assert 'from vgo_installer import materializer' not in content


def test_installer_core_reads_runtime_surface_contracts_from_contracts_package() -> None:
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    materializer = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'materializer.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')
    host_closure = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'host_closure.py').read_text(encoding='utf-8')

    for content in (install_runtime, materializer, uninstall_service, host_closure):
        assert 'vgo_contracts.runtime_surface_contract' in content
        assert 'from runtime_contracts import' not in content
        assert 'scripts/common/resolve_vgo_adapter.py' not in content


def test_installer_core_shares_adapter_registry_resolution_without_script_shims() -> None:
    adapter_registry = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'adapter_registry.py').read_text(encoding='utf-8')
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')

    assert 'def resolve_adapter(' in adapter_registry
    assert 'def resolve_adapter_entries(' in adapter_registry
    assert 'def resolve_bootstrap_choices(' in adapter_registry
    assert 'def resolve_supported_hosts(' in adapter_registry
    assert 'def resolve_target_root_spec(' in adapter_registry
    assert 'def resolve_default_target_root(' in adapter_registry
    assert 'def resolve_matching_target_root_hosts(' in adapter_registry
    assert 'def resolve_target_root_owner(' in adapter_registry
    assert 'from vgo_contracts.adapter_registry_support import (' in adapter_registry
    assert 'def resolve_registry_path(' in adapter_registry
    assert 'from .adapter_registry import resolve_adapter' in install_runtime
    assert 'from .adapter_registry import resolve_adapter' in uninstall_service
    assert 'scripts/common/resolve_vgo_adapter.py' not in install_runtime
    assert 'scripts/common/resolve_vgo_adapter.py' not in uninstall_service


def test_install_runtime_delegates_host_closure_semantics() -> None:
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    host_closure = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'host_closure.py').read_text(encoding='utf-8')

    assert 'from .host_closure import (' in install_runtime
    assert 'install_claude_managed_settings' in install_runtime
    assert 'materialize_host_closure' in install_runtime
    assert 'is_closed_ready_required' in install_runtime

    assert 'def resolve_bridge_command' not in install_runtime
    assert 'def materialize_host_specialist_wrapper' not in install_runtime
    assert 'def install_claude_managed_settings' not in install_runtime
    assert 'def materialize_host_settings' not in install_runtime
    assert 'def materialize_host_closure' not in install_runtime
    assert 'def is_closed_ready_required' not in install_runtime

    assert 'def resolve_bridge_command' in host_closure
    assert 'def materialize_host_specialist_wrapper' in host_closure
    assert 'def install_claude_managed_settings' in host_closure
    assert 'def materialize_host_settings' in host_closure
    assert 'def materialize_host_closure' in host_closure
    assert 'def is_closed_ready_required' in host_closure


def test_install_runtime_delegates_ledger_semantics_to_install_plan_and_service() -> None:
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')

    assert 'from .install_plan import build_install_plan' in install_runtime
    assert 'from .ledger_service import (' in install_runtime
    assert 'MaterializationLedgerState' in install_runtime
    assert 'load_existing_install_ledger' in install_runtime
    assert 'refresh_install_ledger' in install_runtime
    assert 'write_install_ledger' in install_runtime

    assert 'def load_existing_install_ledger' not in install_runtime
    assert 'def derive_managed_skill_names_from_ledger' not in install_runtime
    assert 'def build_payload_summary' not in install_runtime
    assert 'def write_install_ledger' not in install_runtime
    assert 'def refresh_install_ledger' not in install_runtime


def test_install_runtime_delegates_materialization_semantics() -> None:
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    materializer = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'materializer.py').read_text(encoding='utf-8')

    assert 'from .materializer import (' in install_runtime
    assert 'copy_dir_replace' in install_runtime
    assert 'copy_tree' in install_runtime
    assert 'copy_skill_roots_without_self_shadow' in install_runtime
    assert 'copy_file' in install_runtime
    assert 'sync_vibe_canonical' in install_runtime
    assert 'materialize_generated_nested_compatibility' in install_runtime
    assert 'materialize_allowlisted_skills' in install_runtime
    assert 'install_codex_payload' in install_runtime
    assert 'install_opencode_guidance_payload' in install_runtime
    assert 'install_runtime_core_mode_payload' in install_runtime

    assert 'def copy_dir_replace' not in install_runtime
    assert 'def copy_tree' not in install_runtime
    assert 'def copy_skill_roots_without_self_shadow' not in install_runtime
    assert 'def copy_file' not in install_runtime
    assert 'def sync_vibe_canonical' not in install_runtime
    assert 'def materialize_generated_nested_compatibility' not in install_runtime
    assert 'def materialize_allowlisted_skills' not in install_runtime
    assert 'def ensure_skill_present' not in install_runtime
    assert 'def install_codex_payload' not in install_runtime
    assert 'def install_opencode_guidance_payload' not in install_runtime
    assert 'def install_runtime_core_mode_payload' not in install_runtime

    assert 'def copy_dir_replace' in materializer
    assert 'def copy_tree' in materializer
    assert 'def copy_skill_roots_without_self_shadow' in materializer
    assert 'def copy_file' in materializer
    assert 'def sync_vibe_canonical' in materializer
    assert 'def materialize_generated_nested_compatibility' in materializer
    assert 'def materialize_allowlisted_skills' in materializer
    assert 'def ensure_skill_present' in materializer
    assert 'def install_codex_payload' in materializer
    assert 'def install_opencode_guidance_payload' in materializer
    assert 'def install_runtime_core_mode_payload' in materializer


def test_uninstall_runtime_delegates_uninstall_semantics() -> None:
    uninstall_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_runtime.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')

    assert 'from .uninstall_service import apply_uninstall, resolve_adapter, uses_skill_only_activation, write_json' in uninstall_runtime

    assert 'def plan_uninstall' not in uninstall_runtime
    assert 'def apply_uninstall' not in uninstall_runtime
    assert 'def collect_foreign_paths' not in uninstall_runtime
    assert 'def remove_vibeskills_node' not in uninstall_runtime
    assert 'def runtime_core_inventory' not in uninstall_runtime
    assert 'def host_inventory' not in uninstall_runtime

    assert 'def plan_uninstall' in uninstall_service
    assert 'def apply_uninstall' in uninstall_service
    assert 'def collect_foreign_paths' in uninstall_service
    assert 'def remove_vibeskills_node' in uninstall_service
    assert 'def runtime_core_inventory' in uninstall_service
    assert 'def host_inventory' in uninstall_service



def test_installer_core_shares_local_io_helper() -> None:
    shared = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / '_io.py').read_text(encoding='utf-8')
    adapter_registry = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'adapter_registry.py').read_text(encoding='utf-8')
    runtime_packaging = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'runtime_packaging.py').read_text(encoding='utf-8')
    ledger_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'ledger_service.py').read_text(encoding='utf-8')
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')

    assert 'def load_json(' in shared
    assert 'def write_json(' in shared
    assert 'def write_json_file(' in shared

    for content in (adapter_registry, runtime_packaging, ledger_service, install_runtime, uninstall_service):
        assert 'from ._io import ' in content

    for content in (adapter_registry, runtime_packaging):
        assert 'def load_json(' not in content

    for content in (ledger_service, install_runtime, uninstall_service):
        assert 'def load_json(' not in content
        assert 'def write_json_file(' not in content

    for content in (install_runtime, uninstall_service):
        assert 'def write_json(' not in content

def test_installer_core_uses_local_bootstrap_helper_for_contract_path_setup() -> None:
    bootstrap = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / '_bootstrap.py').read_text(encoding='utf-8')
    install_runtime = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'install_runtime.py').read_text(encoding='utf-8')
    materializer = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'materializer.py').read_text(encoding='utf-8')
    host_closure = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'host_closure.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')

    assert 'def ensure_contracts_src_on_path' in bootstrap
    assert 'def ensure_repo_src_on_path' in bootstrap

    for content in (install_runtime, materializer, host_closure, uninstall_service):
        assert 'from ._bootstrap import ensure_contracts_src_on_path' in content or 'from ._bootstrap import ensure_contracts_src_on_path, ensure_repo_src_on_path' in content
        assert 'CONTRACTS_SRC =' not in content

    assert 'ensure_repo_src_on_path(repo_root, "packages/skill-catalog/src")' in install_runtime
