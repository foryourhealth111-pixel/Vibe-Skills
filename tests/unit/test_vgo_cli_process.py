from __future__ import annotations

from io import BytesIO
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

import vgo_cli.process as process


class _BufferingStream:
    def __init__(self, encoding: str = 'gbk') -> None:
        self.encoding = encoding
        self.buffer = BytesIO()

    def write(self, text: str) -> None:
        raise UnicodeEncodeError(self.encoding, text, 0, 1, 'simulated console encoding failure')


def test_print_process_output_falls_back_to_replacement_bytes(monkeypatch) -> None:
    stdout_stream = _BufferingStream()
    stderr_stream = _BufferingStream()
    result = subprocess.CompletedProcess(
        args=['demo'],
        returncode=0,
        stdout='ok\ufffd\n',
        stderr='warn\ufffd\n',
    )

    monkeypatch.setattr(process.sys, 'stdout', stdout_stream)
    monkeypatch.setattr(process.sys, 'stderr', stderr_stream)

    process.print_process_output(result)

    assert stdout_stream.buffer.getvalue().decode('gbk', errors='replace') == 'ok?\n'
    assert stderr_stream.buffer.getvalue().decode('gbk', errors='replace') == 'warn?\n'
