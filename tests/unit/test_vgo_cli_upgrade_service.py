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

    def fake_load_recorded_install_status(
        repo_root_arg: Path,
        target_root_arg: Path,
        host_id: str,
    ) -> dict[str, object]:
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

    monkeypatch.setattr(upgrade_service, "load_recorded_install_status", fake_load_recorded_install_status)
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, status, **kwargs: status,
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
    upgrade_service.save_upgrade_status(
        target_root,
        {
            "installed_version": "3.0.1",
            "installed_commit": "same",
            "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, status, **kwargs: status,
    )
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)
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


def test_upgrade_runtime_uses_recorded_target_install_truth_instead_of_fresh_repo_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "fresh-clone"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    steps: list[str] = []

    upgrade_service.save_upgrade_status(
        target_root,
        {
            "host_id": "codex",
            "target_root": str(target_root.resolve()),
            "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "repo_default_branch": "main",
            "installed_version": "3.0.2",
            "installed_commit": "old-install",
            "installed_recorded_at": "2026-04-10T00:00:00Z",
        },
    )

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "get_official_self_repo_metadata",
        lambda repo_root_arg: {
            "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "default_branch": "main",
            "canonical_root": ".",
        },
    )

    def fake_refresh_upstream(
        repo_root_arg: Path,
        target_root_arg: Path,
        current_status: dict[str, object],
        **kwargs: object,
    ) -> dict[str, object]:
        assert current_status["installed_version"] == "3.0.2"
        assert current_status["installed_commit"] == "old-install"
        return {
            **current_status,
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": True,
            "repo_default_branch": "main",
        }

    monkeypatch.setattr(upgrade_service, "refresh_upstream_status", fake_refresh_upstream)
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda repo_root_arg, branch, target_commit=None: steps.append(f"reset:{branch}:{target_commit}"),
    )
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id, **kwargs: {
            "installed_version": "3.0.3",
            "installed_commit": "new-source-head",
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": False,
        },
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

    assert steps == ["reset:main:new-source-head", "reinstall", "check"]
    assert result["changed"] is True
    assert result["before"]["installed_commit"] == "old-install"
    assert result["after"]["installed_commit"] == "new-source-head"


def test_upgrade_runtime_reinstalls_when_target_root_has_no_recorded_install_truth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "fresh-clone"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    steps: list[str] = []

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "get_official_self_repo_metadata",
        lambda repo_root_arg: {
            "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "default_branch": "main",
            "canonical_root": ".",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status, **kwargs: {
            **current_status,
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": False,
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda repo_root_arg, branch, target_commit=None: steps.append(f"reset:{branch}:{target_commit}"),
    )
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id, **kwargs: {
            "installed_version": "3.0.3",
            "installed_commit": "new-source-head",
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": False,
        },
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

    assert steps == ["reset:main:new-source-head", "reinstall", "check"]
    assert result["changed"] is True
    assert result["before"]["installed_commit"] == ""
    assert result["after"]["installed_commit"] == "new-source-head"


def test_upgrade_runtime_reinstalls_when_recorded_install_version_has_no_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "fresh-clone"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    steps: list[str] = []

    upgrade_service.save_upgrade_status(
        target_root,
        {
            "host_id": "codex",
            "target_root": str(target_root.resolve()),
            "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "repo_default_branch": "main",
            "installed_version": "3.0.3",
            "installed_commit": "",
            "installed_recorded_at": "2026-04-10T00:00:00Z",
        },
    )

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "get_official_self_repo_metadata",
        lambda repo_root_arg: {
            "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "default_branch": "main",
            "canonical_root": ".",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status, **kwargs: {
            **current_status,
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": False,
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda repo_root_arg, branch, target_commit=None: steps.append(f"reset:{branch}:{target_commit}"),
    )
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id, **kwargs: {
            "installed_version": "3.0.3",
            "installed_commit": "new-source-head",
            "remote_latest_version": "3.0.3",
            "remote_latest_commit": "new-source-head",
            "update_available": False,
        },
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

    assert steps == ["reset:main:new-source-head", "reinstall", "check"]
    assert result["changed"] is True
    assert result["before"]["installed_version"] == "3.0.3"
    assert result["before"]["installed_commit"] == ""


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


def test_prepare_managed_upgrade_repo_root_clones_official_source_for_installed_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    installed_runtime = tmp_path / "target" / "skills" / "vibe"
    (installed_runtime / "config").mkdir(parents=True)
    (installed_runtime / "config" / "version-governance.json").write_text(
        '{"source_of_truth":{"official_self_repo":{"repo_url":"https://example.test/Vibe-Skills.git","default_branch":"main"}}}\n',
        encoding="utf-8",
    )
    target_root = tmp_path / "target"
    commands: list[list[str]] = []

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:2] == ["git", "clone"]:
            checkout_root = Path(command[-1])
            (checkout_root / ".git").mkdir(parents=True)
            (checkout_root / "config").mkdir()
            (checkout_root / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    resolved = upgrade_service.prepare_managed_upgrade_repo_root(installed_runtime, target_root)

    assert resolved == (target_root / ".vibeskills" / "upgrade-source").resolve()
    assert commands == [
        [
            "git",
            "clone",
            "--quiet",
            "--branch",
            "main",
            "--single-branch",
            "https://example.test/Vibe-Skills.git",
            str(target_root / ".vibeskills" / "upgrade-source"),
        ]
    ]


def test_upgrade_runtime_uses_managed_source_when_started_from_installed_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    installed_runtime = tmp_path / "target" / "skills" / "vibe"
    installed_runtime.mkdir(parents=True)
    target_root = tmp_path / "target"
    managed_source = target_root / ".vibeskills" / "upgrade-source"
    managed_source.mkdir(parents=True)
    steps: list[str] = []
    recorded: dict[str, object] = {}

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: None)
    monkeypatch.setattr(
        upgrade_service,
        "prepare_managed_upgrade_repo_root",
        lambda repo_root_arg, target_root_arg: managed_source,
    )

    def fake_load_recorded_install_status(repo_root_arg: Path, target_root_arg: Path, host_id: str) -> dict[str, object]:
        recorded["repo_root"] = repo_root_arg
        return {
            "installed_version": "3.0.4",
            "installed_commit": "old-install",
            "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "repo_default_branch": "main",
        }

    monkeypatch.setattr(upgrade_service, "load_recorded_install_status", fake_load_recorded_install_status)
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, status, **kwargs: {
            **status,
            "remote_latest_version": "3.1.0",
            "remote_latest_commit": "new-install",
            "update_available": True,
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda repo_root_arg, branch, target_commit=None: steps.append(f"reset:{repo_root_arg}:{target_commit}"),
    )
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id, **kwargs: {
            "installed_version": "3.1.0",
            "installed_commit": "new-install",
        },
    )

    result = upgrade_service.upgrade_runtime(
        repo_root=installed_runtime,
        target_root=target_root,
        host_id="claude-code",
        profile="full",
        frontend="powershell",
        install_external=False,
        strict_offline=False,
        require_closed_ready=False,
        allow_external_skill_fallback=False,
        skip_runtime_freshness_gate=False,
    )

    assert recorded["repo_root"] == managed_source
    assert steps == [f"reset:{managed_source}:new-install", "reinstall", "check"]
    assert result["changed"] is True
    assert result["after"]["installed_version"] == "3.1.0"


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
    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "load_recorded_install_status",
        lambda repo_root_arg, target_root_arg, host_id: {
            "installed_version": "3.0.0",
            "installed_commit": "old",
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)

    def fake_refresh_upstream(
        repo_root_arg: Path,
        target_root_arg: Path,
        current_status: dict[str, object],
        **kwargs: object,
    ) -> dict[str, object]:
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
    monkeypatch.setattr(
        upgrade_service,
        "reset_repo_to_official_head",
        lambda repo_root_arg, branch, target_commit=None: steps.append(f"reset:{branch}:{target_commit}"),
    )
    monkeypatch.setattr(upgrade_service, "reinstall_runtime", lambda **kwargs: steps.append("reinstall"))
    monkeypatch.setattr(
        upgrade_service,
        "run_upgrade_check",
        lambda **kwargs: (steps.append("check") or subprocess.CompletedProcess(args=["check"], returncode=0, stdout="", stderr="")),
    )
    monkeypatch.setattr(
        upgrade_service,
        "refresh_installed_status",
        lambda repo_root_arg, target_root_arg, host_id, **kwargs: {
            "installed_version": "3.0.1",
            "installed_commit": "new",
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "new",
            "update_available": False,
        },
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

    assert steps == ["refresh", "reset:main:new", "reinstall", "check"]
    assert result["changed"] is True
    assert result["before"]["installed_version"] == "3.0.0"
    assert result["after"]["installed_version"] == "3.0.1"


def test_upgrade_runtime_forces_fresh_upstream_refresh_before_deciding_update(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "load_recorded_install_status",
        lambda repo_root_arg, target_root_arg, host_id: {
            "installed_version": "3.0.0",
            "installed_commit": "local",
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "stale-remote",
            "remote_latest_checked_at": "2026-04-10T00:00:00Z",
            "update_available": True,
        },
    )
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)

    recorded: dict[str, object] = {}

    def fake_refresh_upstream(
        repo_root_arg: Path,
        target_root_arg: Path,
        current_status: dict[str, object],
        *,
        force_refresh: bool = False,
    ) -> dict[str, object]:
        recorded["force_refresh"] = force_refresh
        return {
            **current_status,
            "remote_latest_version": "3.0.0",
            "remote_latest_commit": "local",
            "update_available": False,
        }

    monkeypatch.setattr(upgrade_service, "refresh_upstream_status", fake_refresh_upstream)
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

    assert recorded["force_refresh"] is True
    assert result["changed"] is False


def test_refresh_upstream_status_reads_release_metadata_from_resolved_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    commands: list[list[str]] = []

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert cwd == repo_root
        if command[:3] == ["git", "fetch", "--quiet"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(command, 0, stdout="abc123\n", stderr="")
        if command == ["git", "show", "abc123:config/version-governance.json"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"release":{"version":"3.0.1"}}\n',
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    status = upgrade_service.refresh_upstream_status(
        repo_root,
        target_root,
        {
            "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "repo_default_branch": "main",
            "installed_version": "3.0.0",
            "installed_commit": "old",
        },
        force_refresh=True,
    )

    assert status["remote_latest_commit"] == "abc123"
    assert status["remote_latest_version"] == "3.0.1"
    assert commands == [
        ["git", "fetch", "--quiet", "https://github.com/foryourhealth111-pixel/Vibe-Skills.git", "main"],
        ["git", "rev-parse", "FETCH_HEAD"],
        ["git", "show", "abc123:config/version-governance.json"],
    ]


def test_refresh_upstream_status_falls_back_to_repo_governance_when_cached_remote_metadata_is_blank(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    commands: list[list[str]] = []

    monkeypatch.setattr(
        upgrade_service,
        "get_official_self_repo_metadata",
        lambda repo_root_arg: {
            "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "default_branch": "main",
            "canonical_root": ".",
        },
    )

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert cwd == repo_root
        if command[:3] == ["git", "fetch", "--quiet"]:
            assert command == [
                "git",
                "fetch",
                "--quiet",
                "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
                "main",
            ]
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(command, 0, stdout="abc123\n", stderr="")
        if command == ["git", "show", "abc123:config/version-governance.json"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"release":{"version":"3.0.1"}}\n',
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    status = upgrade_service.refresh_upstream_status(
        repo_root,
        target_root,
        {
            "repo_remote": "",
            "repo_default_branch": "",
            "installed_version": "3.0.0",
            "installed_commit": "old",
        },
        force_refresh=True,
    )

    assert status["remote_latest_commit"] == "abc123"
    assert status["remote_latest_version"] == "3.0.1"
    assert commands[0] == [
        "git",
        "fetch",
        "--quiet",
        "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
        "main",
    ]


def test_upgrade_runtime_does_not_rewrite_existing_status_when_upstream_refresh_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()
    previous_status = {
        "host_id": "codex",
        "target_root": str(target_root.resolve()),
        "repo_remote": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
        "repo_default_branch": "main",
        "installed_version": "3.0.0",
        "installed_commit": "old",
        "installed_recorded_at": "2026-04-10T00:00:00Z",
        "remote_latest_commit": "old",
        "remote_latest_version": "3.0.0",
        "remote_latest_checked_at": "2026-04-10T00:00:00Z",
        "update_available": False,
    }
    upgrade_service.save_upgrade_status(target_root, previous_status)

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "get_official_self_repo_metadata",
        lambda repo_root_arg: {
            "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
            "default_branch": "main",
            "canonical_root": ".",
        },
    )
    monkeypatch.setattr(
        upgrade_service,
        "get_local_release_metadata",
        lambda repo_root_arg: {"version": "3.0.1", "updated": "2026-04-15", "channel": "stable"},
    )
    monkeypatch.setattr(upgrade_service, "get_repo_head_commit", lambda repo_root_arg: "new")

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == repo_root
        if command[:3] == ["git", "fetch", "--quiet"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="network down")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    with pytest.raises(upgrade_service.CliError, match="network down"):
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

    assert upgrade_service.load_upgrade_status(target_root) == previous_status


def test_upgrade_runtime_propagates_refresh_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_root = tmp_path / "target"
    target_root.mkdir()

    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "load_recorded_install_status",
        lambda repo_root_arg, target_root_arg, host_id: {"installed_version": "3.0.0", "installed_commit": "old"},
    )
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status, **kwargs: (_ for _ in ()).throw(upgrade_service.CliError("refresh failed")),
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
    monkeypatch.setattr(upgrade_service, "resolve_upgrade_repo_root", lambda path: repo_root)
    monkeypatch.setattr(
        upgrade_service,
        "load_recorded_install_status",
        lambda repo_root_arg, target_root_arg, host_id: {
            "installed_version": "3.0.0",
            "installed_commit": "old",
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(upgrade_service, "has_recorded_install_truth", lambda status: True)
    monkeypatch.setattr(
        upgrade_service,
        "refresh_upstream_status",
        lambda repo_root_arg, target_root_arg, current_status, **kwargs: {
            **current_status,
            "remote_latest_version": "3.0.1",
            "remote_latest_commit": "new",
            "update_available": True,
            "repo_default_branch": "main",
        },
    )
    monkeypatch.setattr(upgrade_service, "reset_repo_to_official_head", lambda repo_root_arg, branch, target_commit=None: None)
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


def test_reset_repo_to_official_head_uses_explicit_target_commit_when_provided(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    upgrade_service = importlib.import_module("vgo_cli.upgrade_service")

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    commands: list[list[str]] = []

    def fake_run_subprocess(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert cwd == repo_root
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(upgrade_service, "run_subprocess", fake_run_subprocess)

    upgrade_service.reset_repo_to_official_head(repo_root, "main", "abc123")

    assert commands == [
        ["git", "reset", "--hard", "HEAD"],
        ["git", "clean", "-fd"],
        ["git", "checkout", "-B", "main", "abc123"],
        ["git", "reset", "--hard", "abc123"],
    ]
