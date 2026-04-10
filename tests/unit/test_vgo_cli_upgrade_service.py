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

    recorded: dict[str, object] = {}

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: canonical_root)

    def fake_refresh_installed_status(repo_root_arg: Path, target_root_arg: Path, host_id: str) -> dict[str, object]:
        recorded["repo_root"] = repo_root_arg
        recorded["target_root"] = target_root_arg
        recorded["host_id"] = host_id
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
    assert recorded["host_id"] == "codex"


def test_upgrade_runtime_noops_when_install_is_already_current(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id: {
            "installed_version": "3.0.1",
            "installed_commit": "same",
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "same",
            "update_available": False,
        },
    )
    monkeypatch.setattr(upgrade_service, "refresh_upstream_status", lambda repo_root_arg, target_root_arg, status: status)
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reset repo")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "reinstall_runtime",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not reinstall")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not run check")),
    )

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
    assert "already current" in capsys.readouterr().out.lower()


def test_resolve_upgrade_repo_root_does_not_fall_back_to_unrelated_cwd_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "installed-runtime" / "skills" / "vibe"
    repo_root.mkdir(parents=True)

    unrelated_repo = tmp_path / "other-repo"
    (unrelated_repo / ".git").mkdir(parents=True)
    (unrelated_repo / "config").mkdir(parents=True)
    (unrelated_repo / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.chdir(unrelated_repo)

    assert upgrade_service.resolve_upgrade_repo_root(repo_root) is None


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


def test_upgrade_runtime_refreshes_repo_reinstalls_and_checks_when_update_is_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    steps: list[str] = []
    statuses = iter(
        [
            {
                "installed_version": "3.0.0",
                "installed_commit": "old",
                "repo_default_branch": "main",
            },
            {
                "installed_version": "3.0.1",
                "installed_commit": "new",
                "remote_latest_version": "3.0.1",
                "remote_latest_commit": "new",
                "update_available": False,
            },
        ]
    )

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(upgrade_service, "refresh_installed_status", lambda repo_root_arg, target_root_arg, host_id: next(statuses))

    def fake_refresh_upstream(repo_root_arg: Path, target_root_arg: Path, current_status: dict[str, object]) -> dict[str, object]:
        steps.append("refresh")
        merged = dict(current_status)
        merged.update(
            {
                "remote_latest_version": "3.0.1",
                "remote_latest_commit": "new",
                "update_available": True,
                "repo_default_branch": "main",
            }
        )
        return merged

    monkeypatch.setattr(upgrade_service, "refresh_upstream_status", fake_refresh_upstream)
    monkeypatch.setattr(upgrade_service, "reset_repo_to_official_head", lambda repo_root_arg, branch: steps.append(f"reset:{branch}"))
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )

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

    assert steps == ["refresh", "reset:main", "reinstall", "check"]
    assert result["changed"] is True
    assert result["before"]["installed_version"] == "3.0.0"
    assert result["after"]["installed_version"] == "3.0.1"


def test_upgrade_runtime_propagates_refresh_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id: {"installed_version": "3.0.0", "installed_commit": "old"},
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status: (_ for _ in ()).throw(upgrade_service.CliError("refresh failed")),
    )

    with pytest.raises(upgrade_service.CliError, match="refresh failed"):
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


def test_upgrade_runtime_propagates_check_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    statuses = iter(
        [
            {"installed_version": "3.0.0", "installed_commit": "old", "repo_default_branch": "main"},
            {"installed_version": "3.0.1", "installed_commit": "new"},
        ]
    )

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(upgrade_service, "refresh_installed_status", lambda repo_root_arg, target_root_arg, host_id: next(statuses))
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status: {
            **current_status,
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "new",
            "update_available": True,
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(upgrade_service, "reset_repo_to_official_head", lambda repo_root_arg, branch: None)
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: None)
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (_ for _ in ()).throw(upgrade_service.CliError("check failed")),
    )

    with pytest.raises(upgrade_service.CliError, match="check failed"):
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


def test_reinstall_runtime_propagates_strict_offline_to_optional_external_installs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    recorded: dict[str, object] = {}

    monkeypatch.setattr(upgrade_service, "install_mode_for_host", lambda host_id: "governed")
    monkeypatch.setattr(
        upgrade_service,
        "run_installer_core",
        lambda repo_root_arg, command: subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"install_mode":"governed","external_fallback_used":[]}\n',
            stderr="",
        ),
    )
    monkeypatch.setattr(
        upgrade_service,
        "parse_json_output",
        lambda result: {"install_mode": "governed", "external_fallback_used": []},
    )

    def fake_maybe_install_external_dependencies(repo_root_arg: Path, install_mode: str, *, strict_offline: bool = False) -> None:
        recorded["repo_root"] = repo_root_arg
        recorded["install_mode"] = install_mode
        recorded["strict_offline"] = strict_offline

    monkeypatch.setattr(upgrade_service, "maybe_install_external_dependencies", fake_maybe_install_external_dependencies)
    monkeypatch.setattr(upgrade_service, "reconcile_install_postconditions", lambda *args, **kwargs: None)

    upgrade_service.reinstall_runtime(
        repo_root=repo_root,
        target_root=target_root,
        host_id="codex",
        profile="full",
        frontend="shell",
        install_external=True,
        strict_offline=True,
        require_closed_ready=False,
        allow_external_skill_fallback=False,
        skip_runtime_freshness_gate=False,
    )

    assert recorded == {
        "repo_root": repo_root,
        "install_mode": "governed",
        "strict_offline": True,
    }


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
