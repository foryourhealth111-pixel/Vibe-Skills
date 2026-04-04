from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.commands import route_command, runtime_command, verify_command
from vgo_cli.errors import CliError
from vgo_cli.output import parse_json_output, print_install_completion_hint, print_json_payload


def test_parse_json_output_returns_payload() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='{"ok": true}', stderr='')

    assert parse_json_output(result) == {'ok': True}


def test_parse_json_output_rejects_invalid_json() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='not-json', stderr='')

    with pytest.raises(CliError, match='Invalid JSON output from core command'):
        parse_json_output(result)


def test_print_install_completion_hint_for_shell(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    print_install_completion_hint('shell', profile='full', target_root=tmp_path)

    captured = capsys.readouterr()
    assert f'Install done. Run: bash check.sh --profile full --target-root {tmp_path}' in captured.out


def test_route_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_router_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded['repo_root'] = repo_root
        recorded['argv'] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"ok": true}\n', stderr='')

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded['printed_stdout'] = result.stdout

    monkeypatch.setattr(cli_commands, 'run_router_core', fake_run_router_core)
    monkeypatch.setattr(cli_commands, 'print_process_output', fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        prompt='route this',
        grade='XL',
        task_type='debug',
        requested_skill='vibe',
        host_id='codex',
        target_root='/tmp/codex',
        force_runtime_neutral=True,
    )

    assert route_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['argv'] == [
        '--prompt', 'route this',
        '--grade', 'XL',
        '--task-type', 'debug',
        '--requested-skill', 'vibe',
        '--host-id', 'codex',
        '--target-root', '/tmp/codex',
        '--force-runtime-neutral',
    ]
    assert recorded['printed_stdout'] == '{"ok": true}\n'



def test_print_json_payload_emits_pretty_json(capsys: pytest.CaptureFixture[str]) -> None:
    print_json_payload({'ok': True})

    captured = capsys.readouterr()
    assert '{\n  "ok": true\n}' in captured.out



def test_verify_command_uses_runtime_contract_for_powershell_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
        recorded['repo_root'] = repo_root
        return {'coherence_gate': 'scripts/verify/custom-coherence-gate.ps1'}

    def fake_passthrough(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
        recorded['frontend'] = args.frontend
        recorded['shell_script'] = shell_script
        recorded['powershell_script'] = powershell_script
        recorded['rest'] = list(args.rest)
        return 0

    monkeypatch.setattr(cli_commands, 'get_installed_runtime_config', fake_get_installed_runtime_config)
    monkeypatch.setattr(cli_commands, 'passthrough_command', fake_passthrough)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        frontend='powershell',
        rest=['--artifacts'],
    )

    assert verify_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['frontend'] == 'powershell'
    assert recorded['shell_script'] == 'check.sh'
    assert recorded['powershell_script'] == 'scripts/verify/custom-coherence-gate.ps1'
    assert recorded['rest'] == ['--artifacts']



def test_runtime_command_uses_runtime_contract_for_powershell_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
        recorded['repo_root'] = repo_root
        return {'runtime_entrypoint': 'scripts/runtime/custom-runtime-entrypoint.ps1'}

    def fake_passthrough(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
        recorded['frontend'] = args.frontend
        recorded['shell_script'] = shell_script
        recorded['powershell_script'] = powershell_script
        recorded['rest'] = list(args.rest)
        return 0

    monkeypatch.setattr(cli_commands, 'get_installed_runtime_config', fake_get_installed_runtime_config)
    monkeypatch.setattr(cli_commands, 'passthrough_command', fake_passthrough)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        frontend='powershell',
        rest=['--task', 'smoke'],
    )

    assert runtime_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['frontend'] == 'powershell'
    assert recorded['shell_script'] == 'check.sh'
    assert recorded['powershell_script'] == 'scripts/runtime/custom-runtime-entrypoint.ps1'
    assert recorded['rest'] == ['--task', 'smoke']
