from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "governance" / "new-origin-record.ps1"


def _require_powershell() -> str:
    powershell = shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell 7 (pwsh) executable not available in PATH")
    return powershell


def _run_new_origin_record(local_path: str) -> subprocess.CompletedProcess[str]:
    powershell = _require_powershell()
    return subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-CanonicalSlug",
            "pytest-origin",
            "-UpstreamRepo",
            "https://example.invalid/upstream.git",
            "-UpstreamRef",
            "main",
            "-LicenseSpdx",
            "MIT",
            "-DistributionTier",
            "internal",
            "-RedistributionPosture",
            "allowed",
            "-IntegrationMode",
            "mirrored",
            "-LocalPath",
            local_path,
            "-Force",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_new_origin_record_rejects_vendor_root() -> None:
    origin_path = REPO_ROOT / "vendor" / "ORIGIN.md"
    existing = origin_path.read_text(encoding="utf-8") if origin_path.exists() else None

    try:
        if origin_path.exists():
            origin_path.unlink()
        result = _run_new_origin_record("vendor")

        combined = result.stdout + result.stderr
        assert result.returncode != 0
        assert "not at vendor root" in combined
        assert not origin_path.exists()
    finally:
        if origin_path.exists():
            origin_path.unlink()
        if existing is not None:
            origin_path.write_text(existing, encoding="utf-8")


def test_new_origin_record_allows_vendor_subdirectories() -> None:
    relative_dir = Path("vendor") / f"pytest-origin-{uuid.uuid4().hex}"
    target_dir = REPO_ROOT / relative_dir

    try:
        result = _run_new_origin_record(relative_dir.as_posix())

        combined = result.stdout + result.stderr
        assert result.returncode == 0, combined
        assert (target_dir / "ORIGIN.md").exists()
    finally:
        if target_dir.exists():
            shutil.rmtree(target_dir)
