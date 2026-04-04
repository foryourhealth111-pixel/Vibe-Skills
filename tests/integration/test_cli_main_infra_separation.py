from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vgo_cli_main_delegates_hosts_process_install_support_and_commands() -> None:
    content = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'main.py').read_text(encoding='utf-8')

    assert 'from .commands import install_command, passthrough_command, route_command, runtime_command, uninstall_command, verify_command' in content
    assert 'def install_command' not in content
    assert 'def uninstall_command' not in content
    assert 'def passthrough_command' not in content
    assert 'def route_command' not in content
    assert 'def runtime_command' not in content
    assert 'def verify_command' not in content
    assert 'def parse_json_output' not in content
    assert 'def print_install_completion_hint' not in content


def test_vgo_cli_install_gates_delegate_repo_and_process_infrastructure() -> None:
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    install_gates = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_gates.py').read_text(encoding='utf-8')
    repo = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'repo.py').read_text(encoding='utf-8')
    process = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'process.py').read_text(encoding='utf-8')

    assert 'from .repo import get_installed_runtime_config, resolve_canonical_repo_root' not in install_support
    assert 'from .repo import get_installed_runtime_config, resolve_canonical_repo_root' in install_gates
    assert 'from .process import (' in install_gates
    assert 'def load_json(' not in install_gates
    assert 'def load_governance(' not in install_gates
    assert 'def get_installed_runtime_config(' not in install_gates
    assert 'def resolve_canonical_repo_root(' not in install_gates
    assert 'def choose_powershell(' not in install_gates
    assert 'def print_process_output(' not in install_gates
    assert 'def run_powershell_file(' not in install_gates
    assert 'def run_subprocess(' not in install_gates

    assert 'from vgo_contracts.installed_runtime_contract import default_installed_runtime_config, merge_installed_runtime_config' in repo
    assert 'def load_json(' in repo
    assert 'def load_governance(' in repo
    assert 'def get_installed_runtime_config(' in repo
    assert 'def resolve_canonical_repo_root(' in repo
    assert "defaults = {" not in repo
    assert 'def resolve_adapter_registry_path(' not in repo
    assert 'def load_adapter_registry(' not in repo
    assert 'def choose_powershell(' in process
    assert 'def print_process_output(' in process
    assert 'def run_powershell_file(' in process
    assert 'def run_subprocess(' in process


def test_vgo_cli_commands_delegate_external_provisioning() -> None:
    commands = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'commands.py').read_text(encoding='utf-8')
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    external = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'external.py').read_text(encoding='utf-8')

    assert 'from .external import maybe_install_external_dependencies' in commands
    assert 'def maybe_install_external_dependencies(' not in install_support
    assert 'def report_external_fallback_usage(' not in install_support
    assert 'def maybe_install_external_dependencies(' in external
    assert 'def report_external_fallback_usage(' in external


def test_vgo_cli_commands_delegate_output_presentation() -> None:
    commands = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'commands.py').read_text(encoding='utf-8')
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    output = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'output.py').read_text(encoding='utf-8')

    assert 'from .output import parse_json_output, print_install_banner, print_install_completion_hint' in commands
    assert 'def parse_json_output(' not in commands
    assert 'def print_install_banner(' not in commands
    assert 'def print_install_completion_hint(' not in commands
    assert 'def print_install_banner(' not in install_support
    assert 'def parse_json_output(' in output
    assert 'def print_install_banner(' in output
    assert 'def print_install_completion_hint(' in output


def test_vgo_cli_commands_delegate_core_runtime_bridges() -> None:
    commands = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'commands.py').read_text(encoding='utf-8')
    core_bridge = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'core_bridge.py').read_text(encoding='utf-8')

    assert 'from .core_bridge import run_installer_core, run_router_core, run_uninstaller_core' in commands
    assert 'from .workspace import extend_workspace_package_path' not in commands
    assert 'from .process import invoke_python_core' in core_bridge
    assert 'from .workspace import extend_workspace_package_path' in core_bridge
    assert 'from vgo_installer.install_runtime import main as installer_main' not in commands
    assert 'from vgo_installer.uninstall_runtime import main as uninstaller_main' not in commands
    assert 'from vgo_runtime.router_bridge import main as router_main' not in commands
    assert 'def run_installer_core(' in core_bridge
    assert 'def run_uninstaller_core(' in core_bridge
    assert 'def run_router_core(' in core_bridge


def test_vgo_cli_install_support_delegates_installer_bridge_and_json_reporting() -> None:
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    bridge = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'installer_bridge.py').read_text(encoding='utf-8')
    output = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'output.py').read_text(encoding='utf-8')

    assert 'from .installer_bridge import refresh_install_ledger_payload' in install_support
    assert 'from .output import print_json_payload' in install_support
    assert 'def refresh_install_ledger_payload_summary(' not in install_support
    assert 'def refresh_install_ledger_payload(' in bridge
    assert 'def print_json_payload(' in output


def test_vgo_cli_install_support_delegates_skill_surface_quarantine() -> None:
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    skill_surface = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'skill_surface.py').read_text(encoding='utf-8')

    assert 'from .skill_surface import quarantine_codex_duplicate_skill_surface' in install_support
    assert 'def resolve_codex_duplicate_skill_root(' not in install_support
    assert 'def is_vibe_skill_dir(' not in install_support
    assert 'def quarantine_codex_duplicate_skill_surface(' not in install_support
    assert 'def resolve_codex_duplicate_skill_root(' in skill_surface
    assert 'def is_vibe_skill_dir(' in skill_surface
    assert 'def quarantine_codex_duplicate_skill_surface(' in skill_surface


def test_vgo_cli_install_support_delegates_gate_execution() -> None:
    install_support = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_support.py').read_text(encoding='utf-8')
    install_gates = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'install_gates.py').read_text(encoding='utf-8')

    assert 'from .install_gates import run_offline_gate, run_runtime_freshness_gate' in install_support
    assert 'def run_runtime_neutral_freshness_gate(' not in install_support
    assert 'def run_runtime_freshness_gate(' not in install_support
    assert 'def run_offline_gate(' not in install_support
    assert 'def run_runtime_neutral_freshness_gate(' in install_gates
    assert 'def run_runtime_freshness_gate(' in install_gates
    assert 'def run_offline_gate(' in install_gates
