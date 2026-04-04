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
from vgo_cli.hosts import (
    assert_target_root_matches_host_intent,
    install_mode_for_host,
    normalize_host_id,
    resolve_default_target_root,
)
from vgo_cli.process import invoke_python_core, run_powershell_file
import vgo_cli.process as cli_process


def test_normalize_host_id_supports_aliases_and_rejects_unknown() -> None:
    assert normalize_host_id('claude') == 'claude-code'
    assert normalize_host_id('codex') == 'codex'
    with pytest.raises(CliError, match='Unsupported host id'):
        normalize_host_id('unknown-host')


def test_install_mode_for_host_reads_registry_projection() -> None:
    assert install_mode_for_host('windsurf') == 'runtime-core'


def test_resolve_default_target_root_uses_registry_env_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('WINDSURF_HOME', '/tmp/windsurf-home')
    assert resolve_default_target_root('windsurf') == Path('/tmp/windsurf-home')


def test_assert_target_root_matches_host_intent_rejects_host_mismatch(tmp_path: Path) -> None:
    with pytest.raises(CliError, match='Cursor'):
        assert_target_root_matches_host_intent(tmp_path / '.cursor', 'codex')


def test_assert_target_root_matches_host_intent_preserves_opencode_repo_local_guard(tmp_path: Path) -> None:
    with pytest.raises(CliError, match='OpenCode'):
        assert_target_root_matches_host_intent(tmp_path / '.opencode', 'codex')


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

    def fake_run_subprocess(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        recorded['command'] = list(command)
        recorded['cwd'] = cwd
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout='', stderr='')

    monkeypatch.setattr(cli_process, 'choose_powershell', lambda: '/usr/bin/pwsh')
    monkeypatch.setattr(cli_process, 'run_subprocess', fake_run_subprocess)

    result = run_powershell_file(Path('/tmp/test.ps1'), '-TargetRoot', '/tmp/out')

    assert result.returncode == 0
    assert recorded['command'] == [
        '/usr/bin/pwsh',
        '-NoProfile',
        '-File',
        '/tmp/test.ps1',
        '-TargetRoot',
        '/tmp/out',
    ]
