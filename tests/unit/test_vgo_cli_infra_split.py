from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.errors import CliError
import vgo_cli.hosts as cli_hosts
from vgo_cli.hosts import (
    install_mode_for_host,
    normalize_host_id,
    resolve_default_target_root,
)
from vgo_cli.process import invoke_python_core, run_powershell_file
import vgo_cli.process as cli_process


def test_normalize_host_id_supports_aliases_and_defaults_unknown_to_registry_default() -> None:
    assert normalize_host_id('claude') == 'claude-code'
    assert normalize_host_id('codex') == 'codex'
    assert normalize_host_id('unknown-host') == 'codex'


def test_workspace_repo_root_resolution_no_longer_requires_installer_core(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_module_path = tmp_path / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'hosts.py'
    fake_module_path.parent.mkdir(parents=True)
    fake_module_path.write_text('# test shim\n', encoding='utf-8')
    (tmp_path / 'config').mkdir(parents=True)
    (tmp_path / 'config' / 'adapter-registry.json').write_text('{"schema_version":1,"default_adapter_id":"codex","adapters":[]}\n', encoding='utf-8')

    monkeypatch.setattr(cli_hosts, '__file__', str(fake_module_path))
    cli_hosts._resolve_workspace_repo_root.cache_clear()
    try:
        assert cli_hosts._resolve_workspace_repo_root() == tmp_path.resolve()
    finally:
        cli_hosts._resolve_workspace_repo_root.cache_clear()


def test_install_mode_for_host_reads_registry_projection() -> None:
    assert install_mode_for_host('windsurf') == 'runtime-core'


def test_resolve_default_target_root_uses_registry_env_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('VIBE_AGENTS_HOME', '/tmp/agents-home')
    assert resolve_default_target_root('windsurf') == Path('/tmp/agents-home').resolve()


def test_invoke_python_core_captures_output_and_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    def fake_main(argv: list[str] | None = None) -> int:
        print('stdout-line')
        print('stderr-line', file=sys.stderr)
        return 7

    result = invoke_python_core(fake_main, ['--flag'])

    assert result.args == ['--flag']
    assert result.returncode == 7
    assert result.stdout == 'stdout-line\n'
    assert result.stderr == 'stderr-line\n'
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_run_powershell_file_composes_no_profile_command(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}
    script_path = Path('/tmp/test.ps1')

    def fake_run_subprocess(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        recorded['command'] = list(command)
        recorded['cwd'] = cwd
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout='', stderr='')

    def fake_choose_powershell(*, return_diagnostics: bool = False) -> dict[str, object] | str:
        assert return_diagnostics is True
        return {
            'host_path': '/usr/bin/pwsh',
            'host_kind': 'pwsh',
            'fallback_used': False,
            'candidates_checked': [],
            'policy': {},
        }

    monkeypatch.setattr(cli_process, 'choose_powershell', fake_choose_powershell)
    monkeypatch.setattr(cli_process, 'run_subprocess', fake_run_subprocess)

    result = run_powershell_file(script_path, '-TargetRoot', '/tmp/out')

    assert result.returncode == 0
    assert recorded['command'] == [
        '/usr/bin/pwsh',
        '-NoProfile',
        '-File',
        str(script_path),
        '-TargetRoot',
        '/tmp/out',
    ]


def test_run_powershell_file_adds_execution_policy_for_windows_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}
    script_path = Path('/tmp/test.ps1')

    def fake_run_subprocess(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        recorded['command'] = list(command)
        recorded['cwd'] = cwd
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout='', stderr='')

    def fake_choose_powershell(*, return_diagnostics: bool = False) -> dict[str, object]:
        assert return_diagnostics is True
        return {
            'host_path': 'powershell.exe',
            'host_kind': 'windows-powershell',
            'fallback_used': True,
            'candidates_checked': [],
            'policy': {},
        }

    monkeypatch.setattr(cli_process, 'choose_powershell', fake_choose_powershell)
    monkeypatch.setattr(cli_process, 'run_subprocess', fake_run_subprocess)

    result = run_powershell_file(script_path, '-TargetRoot', '/tmp/out')

    assert result.returncode == 0
    assert recorded['command'] == [
        'powershell.exe',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        str(script_path),
        '-TargetRoot',
        '/tmp/out',
    ]


def test_run_powershell_file_error_includes_script_and_resolution_details(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path('/tmp/test.ps1')

    def fake_choose_powershell(*, return_diagnostics: bool = False) -> dict[str, object]:
        assert return_diagnostics is True
        return {
            'host_path': None,
            'host_kind': None,
            'fallback_used': False,
            'candidates_checked': [
                {'candidate_name': 'path-pwsh', 'candidate_path': None},
                {'candidate_name': 'default-pwsh', 'candidate_path': r'C:\Program Files\PowerShell\7\pwsh.exe'},
            ],
            'policy': {},
            'error': 'pwsh is required on non-Windows hosts',
        }

    monkeypatch.setattr(cli_process, 'choose_powershell', fake_choose_powershell)

    with pytest.raises(CliError) as excinfo:
        run_powershell_file(script_path, '-TargetRoot', '/tmp/out')

    message = str(excinfo.value)
    assert str(script_path) in message
    assert 'pwsh is required on non-Windows hosts' in message
    assert 'path-pwsh' in message
    assert r'C:\Program Files\PowerShell\7\pwsh.exe' in message
