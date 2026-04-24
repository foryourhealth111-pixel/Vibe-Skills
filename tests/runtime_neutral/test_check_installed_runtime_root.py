from __future__ import annotations

import json
import locale
import os
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def _run_path_tool(tool_name: str, flag: str, path: Path) -> str | None:
    tool = shutil.which(tool_name)
    if not tool:
        return None

    try:
        converted = subprocess.run(
            [tool, flag, str(path.resolve())],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = converted.stdout.strip()
    return value or None


def _bash_looks_like_wsl() -> bool:
    bash = shutil.which("bash")
    if not bash:
        return False

    normalized = bash.replace("/", "\\").lower()
    return normalized.endswith("\\windows\\system32\\bash.exe")


def _to_bash_path(path: Path) -> str:
    resolved_path = path.resolve()
    resolved = str(resolved_path).replace("\\", "/")
    if len(resolved) >= 3 and resolved[1:3] == ':/':
        if not _bash_looks_like_wsl():
            converted = _run_path_tool("cygpath", "-u", resolved_path) or _run_path_tool("wslpath", "-u", resolved_path)
            if converted:
                return converted
        return f"/mnt/{resolved[0].lower()}/{resolved[3:]}"
    return resolved


def _powershell_requires_windows_paths(powershell: str | None) -> bool:
    if os.name == "nt":
        return True
    if not powershell:
        return False
    executable = Path(powershell).name.casefold()
    return executable in {"powershell", "powershell.exe"}


def _to_windows_path(path: Path, powershell: str | None = None) -> str:
    resolved_path = path.resolve()
    resolved = str(resolved_path)
    if os.name == "nt" or (len(resolved) >= 3 and resolved[1:3] == ':/'):
        return resolved

    if not _powershell_requires_windows_paths(powershell):
        return resolved

    converted = _run_path_tool("cygpath", "-w", resolved_path) or _run_path_tool("wslpath", "-w", resolved_path)
    if converted:
        return converted

    normalized = resolved.replace("\\", "/")
    if normalized.startswith("/mnt/") and len(normalized) > 6 and normalized[5].isalpha() and normalized[6] == "/":
        rest = normalized[7:].replace("/", "\\")
        return f"{normalized[5].upper()}:\\{rest}"
    if normalized.startswith("/") and len(normalized) > 3 and normalized[1].isalpha() and normalized[2] == "/":
        rest = normalized[3:].replace("/", "\\")
        return f"{normalized[1].upper()}:\\{rest}"
    return resolved


def _capture_text_kwargs() -> dict[str, object]:
    encoding = "utf-8"
    if not shutil.which("pwsh") and not shutil.which("pwsh.exe"):
        encoding = locale.getpreferredencoding(False) or "utf-8"
    return {
        "capture_output": True,
        "text": True,
        "encoding": encoding,
        "errors": "replace",
    }


def _repo_temp_dir() -> Path:
    root = REPO_ROOT / ".pytest_tmp" / f"check-installed-runtime-root-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_to_windows_path_does_not_require_cygpath_for_native_windows_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run should not be used for native Windows paths")

    monkeypatch.setattr(os, "name", "nt", raising=False)
    monkeypatch.setattr(subprocess, "run", fail_run)

    assert _to_windows_path(tmp_path).lower() == str(tmp_path.resolve()).lower()


def test_to_windows_path_keeps_posix_path_for_pwsh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run should not be used when pwsh accepts POSIX paths")

    monkeypatch.setattr(subprocess, "run", fail_run)

    assert _to_windows_path(tmp_path, powershell="/usr/bin/pwsh") == str(tmp_path.resolve())


def test_to_bash_path_prefers_cygpath_for_non_wsl_bash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_which(name: str) -> str | None:
        if name == "bash":
            return r"D:\tool\Git\bin\bash.exe"
        if name == "cygpath":
            return r"D:\tool\Git\usr\bin\cygpath.exe"
        return None

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert args[:2] == [r"D:\tool\Git\usr\bin\cygpath.exe", "-u"]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="/f/test/example\n", stderr="")

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _to_bash_path(tmp_path) == "/f/test/example"


def install_minimal_codex_runtime(target_root: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            "install.sh",
            "--host",
            "codex",
            "--profile",
            "minimal",
            "--skip-runtime-freshness-gate",
            "--target-root",
            _to_bash_path(target_root),
        ],
        cwd=REPO_ROOT,
        **_capture_text_kwargs(),
    )
    if result.returncode != 0:
        raise AssertionError(f"install failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")


class CheckInstalledRuntimeRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._baseline_temp_root = _repo_temp_dir()
        cls._baseline_target_root = cls._baseline_temp_root / ".codex"
        install_minimal_codex_runtime(cls._baseline_target_root)

    @classmethod
    def tearDownClass(cls) -> None:
        baseline_root = getattr(cls, "_baseline_temp_root", None)
        if isinstance(baseline_root, Path):
            shutil.rmtree(baseline_root, ignore_errors=True)
        super().tearDownClass()

    def _fresh_installed_runtime(self) -> tuple[Path, Path]:
        temp_root = _repo_temp_dir()
        self.addCleanup(lambda: shutil.rmtree(temp_root, ignore_errors=True))
        target_root = temp_root / ".codex"
        # Avoid repeating the WSL-backed installer for every test on Windows.
        shutil.copytree(self._baseline_target_root, target_root)
        return target_root, target_root / "skills" / "vibe"

    def test_check_sh_accepts_installed_runtime_root(self) -> None:
        target_root, installed_root = self._fresh_installed_runtime()

        result = subprocess.run(
            [
                "bash",
                "check.sh",
                "--host",
                "codex",
                "--profile",
                "minimal",
                "--skip-runtime-freshness-gate",
                "--target-root",
                _to_bash_path(installed_root),
            ],
            cwd=REPO_ROOT,
            **_capture_text_kwargs(),
        )

        self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        self.assertNotIn("skills/vibe/skills/vibe", result.stdout)

    def test_check_sh_fails_closed_when_projection_manifest_is_missing(self) -> None:
        target_root, installed_root = self._fresh_installed_runtime()
        for manifest_path in (
            installed_root / "config" / "runtime-core-packaging.minimal.json",
            installed_root / "config" / "runtime-core-packaging.json",
        ):
            if manifest_path.exists():
                manifest_path.unlink()

        result = subprocess.run(
            [
                "bash",
                "check.sh",
                "--host",
                "codex",
                "--profile",
                "minimal",
                "--skip-runtime-freshness-gate",
                "--target-root",
                _to_bash_path(installed_root),
            ],
            cwd=REPO_ROOT,
            **_capture_text_kwargs(),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Required packaging manifest missing or unreadable", result.stderr)

    def test_check_ps1_accepts_installed_runtime_root(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root, installed_root = self._fresh_installed_runtime()

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                _to_windows_path(installed_root / "check.ps1", powershell),
                "-HostId",
                "codex",
                "-Profile",
                "minimal",
                "-SkipRuntimeFreshnessGate",
                "-TargetRoot",
                _to_windows_path(installed_root, powershell),
            ],
            cwd=REPO_ROOT,
            **_capture_text_kwargs(),
        )

        self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        normalized_stdout = result.stdout.replace("\\", "/")
        self.assertNotIn("skills/vibe/skills/vibe", normalized_stdout)

    def test_check_ps1_reports_invalid_receipt_version_without_crashing(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root, installed_root = self._fresh_installed_runtime()
        installed_governance = json.loads(
            (installed_root / "config" / "version-governance.json").read_text(encoding="utf-8-sig")
        )
        release = installed_governance.get("release") or {}
        receipt_path = installed_root / "outputs" / "runtime-freshness-receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "gate_result": "PASS",
                    "receipt_version": "abc",
                    "target_root": str(target_root),
                    "installed_root": str(installed_root),
                    "release": {
                        "version": str(release.get("version") or ""),
                        "updated": str(release.get("updated") or ""),
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                _to_windows_path(installed_root / "check.ps1", powershell),
                "-HostId",
                "codex",
                "-Profile",
                "minimal",
                "-TargetRoot",
                _to_windows_path(target_root, powershell),
            ],
            cwd=REPO_ROOT,
            **_capture_text_kwargs(),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("[FAIL] vibe runtime freshness receipt version", result.stdout)
        self.assertNotIn("Cannot convert value", result.stderr)

    def test_check_ps1_fails_closed_when_expected_receipt_contract_version_is_invalid(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root, installed_root = self._fresh_installed_runtime()
        governance_path = installed_root / "config" / "version-governance.json"
        installed_governance = json.loads(governance_path.read_text(encoding="utf-8-sig"))
        installed_governance["runtime"]["installed_runtime"]["receipt_contract_version"] = "abc"
        governance_path.write_text(json.dumps(installed_governance) + "\n", encoding="utf-8")

        release = installed_governance.get("release") or {}
        receipt_path = installed_root / "outputs" / "runtime-freshness-receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "gate_result": "PASS",
                    "receipt_version": 2,
                    "target_root": str(target_root),
                    "installed_root": str(installed_root),
                    "release": {
                        "version": str(release.get("version") or ""),
                        "updated": str(release.get("updated") or ""),
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                _to_windows_path(installed_root / "check.ps1", powershell),
                "-HostId",
                "codex",
                "-Profile",
                "minimal",
                "-TargetRoot",
                _to_windows_path(target_root, powershell),
            ],
            cwd=REPO_ROOT,
            **_capture_text_kwargs(),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("[FAIL] vibe runtime freshness receipt version", result.stdout)
        self.assertIn("expected=", result.stdout)


if __name__ == "__main__":
    unittest.main()
