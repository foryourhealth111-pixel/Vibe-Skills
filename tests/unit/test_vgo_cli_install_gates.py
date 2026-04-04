from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.install_gates import run_runtime_neutral_freshness_gate
import vgo_cli.install_gates as install_gates


def test_run_runtime_neutral_freshness_gate_returns_none_when_script_missing(tmp_path: Path) -> None:
    assert run_runtime_neutral_freshness_gate(tmp_path, tmp_path / 'target', 'scripts/verify/runtime_neutral/freshness_gate.py') is None


def test_run_runtime_neutral_freshness_gate_executes_python_gate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    gate_relpath = 'scripts/verify/runtime_neutral/freshness_gate.py'
    gate_path = tmp_path / gate_relpath
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text('print("ok")\n', encoding='utf-8')

    recorded: dict[str, object] = {}

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        recorded['command'] = list(command)
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout='', stderr='')

    monkeypatch.setattr(install_gates, 'run_subprocess', fake_run)

    result = run_runtime_neutral_freshness_gate(tmp_path, tmp_path / 'target', gate_relpath)

    assert result is not None
    assert recorded['command'] == [sys.executable, str(gate_path), '--target-root', str(tmp_path / 'target'), '--write-receipt']
