from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "apps" / "vgo-cli" / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))


def test_upgrade_runtime_resolves_canonical_git_root_before_refresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "installed-runtime" / "skills" / "vibe"
    repo_root.mkdir(parents=True)
    target_root = tmp_path / ".codex"
    target_root.mkdir()
    canonical_root = tmp_path / "repo"
    canonical_root.mkdir()

    recorded: dict[str, Path] = {}

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: canonical_root)

    def fake_refresh_installed_status(repo_root_arg: Path, target_root_arg: Path, host_id: str) -> dict[str, object]:
        recorded["repo_root"] = repo_root_arg
        recorded["target_root"] = target_root_arg
        recorded["host_id"] = Path(host_id)
        return {
            "installed_version": "3.0.1",
            "installed_commit": "same",
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "same",
            "update_available": False,
        }

    monkeypatch.setattr(upgrade_service, "refresh_installed_status", fake_refresh_installed_status)
    monkeypatch.setattr(upgrade_service, "refresh_upstream_status", lambda repo_root_arg, target_root_arg, status: status)

    result = upgrade_service.upgrade_runtime(
        repo_root=repo_root,
        target_root=target_root,
        host_id="codex",
        profile="full",
        frontend="shell",
        install_external=False,
        strict_offline=False,
        require_closed_ready=False,
        allow_external_skill_fallback=False,
        skip_runtime_freshness_gate=False,
    )

    assert result["changed"] is False
    assert recorded["repo_root"] == canonical_root
    assert recorded["target_root"] == target_root


def test_upgrade_runtime_raises_clear_error_when_no_canonical_git_repo_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "installed-runtime" / "skills" / "vibe"
    repo_root.mkdir(parents=True)
    target_root = tmp_path / ".codex"
    target_root.mkdir()

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: None)

    with pytest.raises(upgrade_service.CliError, match="canonical git checkout"):
        upgrade_service.upgrade_runtime(
            repo_root=repo_root,
            target_root=target_root,
            host_id="codex",
            profile="full",
            frontend="shell",
            install_external=False,
            strict_offline=False,
            require_closed_ready=False,
            allow_external_skill_fallback=False,
            skip_runtime_freshness_gate=False,
        )


def test_reset_repo_to_official_head_discards_local_changes_before_switch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    commands: list[list[str]] = []

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert cwd == repo_root
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    upgrade_service.reset_repo_to_official_head(repo_root, "main")

    assert commands == [
        ["git", "reset", "--hard", "HEAD"],
        ["git", "clean", "-fd"],
        ["git", "checkout", "-B", "main", "FETCH_HEAD"],
        ["git", "reset", "--hard", "FETCH_HEAD"],
    ]
