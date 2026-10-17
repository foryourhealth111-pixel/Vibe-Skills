from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages/runtime-core/src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.powershell_bridge import run_powershell_json_command


def _stop_test_descendant(ready: Path) -> None:
    if not ready.is_file():
        return
    pid = int(ready.read_text(encoding="utf-8"))
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, check=False, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.parametrize("inherit_output", [False, True])
@pytest.mark.parametrize("shell", ["python", "powershell"])
def test_bridge_timeout_prevents_descendant_writes_after_return(
    tmp_path: Path, inherit_output: bool, shell: str,
) -> None:
    ready = tmp_path / "child-started"
    release = tmp_path / "release-child"
    marker = tmp_path / "late-evidence.json"
    child = (
        "import os, time; from pathlib import Path\n"
        f"Path({str(ready)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
        "deadline = time.monotonic() + 8\n"
        "while time.monotonic() < deadline:\n"
        f"    if Path({str(release)!r}).exists():\n"
        f"        Path({str(marker)!r}).write_text('late evidence', encoding='utf-8')\n"
        "        break\n"
        "    time.sleep(0.02)\n"
    )
    output_options = "" if inherit_output else "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, "
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}], "
        "stdin=subprocess.DEVNULL, " + output_options
        + "creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)); time.sleep(20)"
    )
    command = [sys.executable, "-c", parent]
    if shell == "powershell":
        powershell = shutil.which("pwsh")
        if powershell is None:
            pytest.skip("PowerShell is unavailable")
        executable = sys.executable.replace("'", "''")
        script = parent.replace("'", "''")
        command = [powershell, "-NoProfile", "-Command", f"& '{executable}' -c '{script}'"]
    started = time.monotonic()
    try:
        with pytest.raises(RuntimeError, match="timed out"):
            run_powershell_json_command(
                command, cwd=tmp_path,
                bridge_label="test native runtime bridge", timeout=2,
            )
        assert time.monotonic() - started < 6, "inherited pipes must not delay timeout cleanup"
        assert ready.is_file(), "the descendant must start before the timeout"
        release.write_text("write evidence", encoding="utf-8")
        deadline = time.monotonic() + 0.75
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(0.02)
        assert not marker.exists(), "timed-out descendants must stop before the bridge returns"
    finally:
        _stop_test_descendant(ready)


def test_bridge_preserves_json_environment_and_working_directory(tmp_path: Path) -> None:
    environment = {**os.environ, "VGO_PROCESS_TREE_TEST": "native environment"}
    script = (
        "import json, os; from pathlib import Path; "
        "print(json.dumps({'cwd': str(Path.cwd()), 'value': os.environ['VGO_PROCESS_TREE_TEST']}))"
    )
    result = run_powershell_json_command(
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        bridge_label="native JSON bridge", timeout=10,
    )
    assert result == {"cwd": str(tmp_path), "value": "native environment"}


def test_bridge_preserves_nonzero_exit_diagnostics(tmp_path: Path) -> None:
    script = "import sys; sys.stderr.write('native failure'); sys.exit(7)"
    with pytest.raises(RuntimeError, match="exit=7.*native failure"):
        run_powershell_json_command(
            [sys.executable, "-c", script], cwd=tmp_path,
            bridge_label="native failure bridge", timeout=10,
        )


def test_bridge_preserves_partial_output_on_timeout(tmp_path: Path) -> None:
    script = "import sys, time; print('partial output', flush=True); print('partial error', file=sys.stderr, flush=True); time.sleep(20)"
    with pytest.raises(RuntimeError, match="timed out.*partial output.*partial error"):
        run_powershell_json_command(
            [sys.executable, "-c", script], cwd=tmp_path,
            bridge_label="native partial-output bridge", timeout=2,
        )


def test_bridge_reads_json_output_file_with_diagnostic_stdout(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    script = (
        "from pathlib import Path; "
        f"Path({str(output)!r}).write_text('{{\"ok\": true}}', encoding='utf-8'); "
        "print('native diagnostic')"
    )
    result = run_powershell_json_command(
        [sys.executable, "-c", script], cwd=tmp_path,
        bridge_label="native output-file bridge", timeout=10, json_output_path=output,
    )
    assert result == {"ok": True}


def test_bridge_still_rejects_non_object_json(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="returned (?:invalid JSON stdout|non-object payload)"):
        run_powershell_json_command(
            [sys.executable, "-c", "print('[]')"], cwd=tmp_path,
            bridge_label="native invalid-JSON bridge", timeout=10,
        )
