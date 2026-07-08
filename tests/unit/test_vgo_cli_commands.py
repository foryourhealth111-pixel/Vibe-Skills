from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.commands import canonical_entry_command, check_command, compatibility_exit_command, index_command, inspect_run_command, install_command, locate_entry_command, route_command, run_command, runtime_command, uninstall_command, update_command, upgrade_command, verify_command
from vgo_cli.errors import CliError
from vgo_cli.main import build_parser
from vgo_cli.output import parse_json_output, print_json_payload


def test_parse_json_output_returns_payload() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='{"ok": true}', stderr='')

    assert parse_json_output(result) == {'ok': True}


def test_parse_json_output_rejects_invalid_json() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='not-json', stderr='')

    with pytest.raises(CliError, match='Invalid JSON output from core command'):
        parse_json_output(result)


def test_route_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_router_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded['repo_root'] = repo_root
        recorded['argv'] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"ok": true}\n', stderr='')

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded['printed_stdout'] = result.stdout

    monkeypatch.setattr(cli_commands, 'run_router_core', fake_run_router_core)
    monkeypatch.setattr(cli_commands, 'print_process_output', fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        prompt='route this',
        grade='XL',
        task_type='debug',
        requested_skill='vibe',
        host_id='codex',
        target_root='/tmp/codex',
        force_runtime_neutral=True,
    )

    assert route_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['argv'] == [
        '--prompt', 'route this',
        '--grade', 'XL',
        '--task-type', 'debug',
        '--requested-skill', 'vibe',
        '--host-id', 'codex',
        '--target-root', '/tmp/codex',
        '--force-runtime-neutral',
    ]
    assert recorded['printed_stdout'] == '{"ok": true}\n'


def test_index_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_skill_index_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded["repo_root"] = repo_root
        recorded["argv"] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"skill_count": 1}\n', stderr="")

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded["printed_stdout"] = result.stdout

    monkeypatch.setattr(cli_commands, "run_skill_index_core", fake_run_skill_index_core)
    monkeypatch.setattr(cli_commands, "print_process_output", fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path / "repo"),
        agent_root=str(tmp_path / "agent"),
        host_id="codex",
        workspace_root=str(tmp_path / "workspace"),
        json=True,
    )

    assert index_command(args) == 0
    assert recorded["repo_root"] == (tmp_path / "repo").resolve()
    assert recorded["argv"] == [
        "--agent-root", str(tmp_path / "agent"),
        "--host-id", "codex",
        "--workspace-root", str(tmp_path / "workspace"),
        "--json",
    ]
    assert recorded["printed_stdout"] == '{"skill_count": 1}\n'


def test_run_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_local_kernel_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded["repo_root"] = repo_root
        recorded["argv"] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"run_id": "run-1"}\n', stderr="")

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded["printed_stdout"] = result.stdout

    monkeypatch.setattr(cli_commands, "run_local_kernel_core", fake_run_local_kernel_core)
    monkeypatch.setattr(cli_commands, "print_process_output", fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path / "repo"),
        agent_root=str(tmp_path / "agent"),
        prompt="Review the runtime redesign.",
        run_id="run-1",
        host_id="codex",
        workspace_root=str(tmp_path / "workspace"),
        json=True,
    )

    assert run_command(args) == 0
    assert recorded["repo_root"] == (tmp_path / "repo").resolve()
    assert recorded["argv"] == [
        "--agent-root", str(tmp_path / "agent"),
        "--prompt", "Review the runtime redesign.",
        "--run-id", "run-1",
        "--host-id", "codex",
        "--workspace-root", str(tmp_path / "workspace"),
        "--json",
    ]
    assert recorded["printed_stdout"] == '{"run_id": "run-1"}\n'


def test_inspect_run_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_inspect_run_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded["repo_root"] = repo_root
        recorded["argv"] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"run_id": "run-1", "summary": {"proof_ready": true}}\n', stderr="")

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded["printed_stdout"] = result.stdout

    monkeypatch.setattr(cli_commands, "run_inspect_run_core", fake_run_inspect_run_core)
    monkeypatch.setattr(cli_commands, "print_process_output", fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path / "repo"),
        agent_root=str(tmp_path / "agent"),
        run_id="run-1",
        host_id="codex",
        workspace_root=str(tmp_path / "workspace"),
    )

    assert inspect_run_command(args) == 0
    assert recorded["repo_root"] == (tmp_path / "repo").resolve()
    assert recorded["argv"] == [
        "--agent-root", str(tmp_path / "agent"),
        "--run-id", "run-1",
        "--host-id", "codex",
        "--workspace-root", str(tmp_path / "workspace"),
    ]
    assert recorded["printed_stdout"] == '{"run_id": "run-1", "summary": {"proof_ready": true}}\n'


def test_locate_entry_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_entry_locator_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded["repo_root"] = repo_root
        recorded["argv"] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"primary_entry_file":"x.py"}\n', stderr="")

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded["printed_stdout"] = result.stdout

    monkeypatch.setattr(cli_commands, "run_entry_locator_core", fake_run_entry_locator_core)
    monkeypatch.setattr(cli_commands, "print_process_output", fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path / "repo"),
        change_kind="planning",
    )

    assert locate_entry_command(args) == 0
    assert recorded["repo_root"] == (tmp_path / "repo").resolve()
    assert recorded["argv"] == [
        "--repo-root", str((tmp_path / "repo").resolve()),
        "--change-kind", "planning",
    ]
    assert recorded["printed_stdout"] == '{"primary_entry_file":"x.py"}\n'


def test_compatibility_exit_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_compatibility_exit_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded["repo_root"] = repo_root
        recorded["argv"] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"controlled_capabilities":[]}\n', stderr="")

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded["printed_stdout"] = result.stdout

    monkeypatch.setattr(cli_commands, "run_compatibility_exit_core", fake_run_compatibility_exit_core)
    monkeypatch.setattr(cli_commands, "print_process_output", fake_print)

    args = argparse.Namespace(
        repo_root=str(tmp_path / "repo"),
    )

    assert compatibility_exit_command(args) == 0
    assert recorded["repo_root"] == (tmp_path / "repo").resolve()
    assert recorded["argv"] == [
        "--repo-root", str((tmp_path / "repo").resolve()),
    ]
    assert recorded["printed_stdout"] == '{"controlled_capabilities":[]}\n'


def test_canonical_entry_command_delegates_to_runtime_core_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_run_canonical_entry_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded['repo_root'] = repo_root
        recorded['argv'] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='{"run_id":"r1"}\n', stderr='')

    def fake_print(result: subprocess.CompletedProcess[str]) -> None:
        recorded['printed_stdout'] = result.stdout

    monkeypatch.setattr(cli_commands, 'run_canonical_entry_core', fake_run_canonical_entry_core)
    monkeypatch.setattr(cli_commands, 'print_process_output', fake_print)
    monkeypatch.setattr(cli_commands, 'normalize_host_id', lambda host_id: 'codex')

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        prompt='plan runtime entry hardening',
        host_id='CoDeX',
        entry_id='vibe',
        requested_stage_stop='phase_cleanup',
        requested_grade_floor='XL',
        artifact_root=str(tmp_path / 'artifacts'),
        local_agent_root=str(tmp_path / 'agent-root'),
        run_id='run-123',
        continue_from_run_id='prior-run',
        bounded_reentry_token='token-123',
        host_decision_json_file=str(tmp_path / 'host-decision.json'),
        force_runtime_neutral=True,
    )

    assert canonical_entry_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['argv'] == [
        '--repo-root', str(tmp_path.resolve()),
        '--host-id', 'codex',
        '--entry-id', 'vibe',
        '--prompt', 'plan runtime entry hardening',
        '--requested-stage-stop', 'phase_cleanup',
        '--requested-grade-floor', 'XL',
        '--run-id', 'run-123',
        '--artifact-root', str((tmp_path / 'artifacts')),
        '--local-agent-root', str(tmp_path / 'agent-root'),
        '--continue-from-run-id', 'prior-run',
        '--bounded-reentry-token', 'token-123',
        '--host-decision-json-file', str(tmp_path / 'host-decision.json'),
        '--force-runtime-neutral',
    ]
    assert recorded['printed_stdout'] == '{"run_id":"r1"}\n'



def test_print_json_payload_emits_pretty_json(capsys: pytest.CaptureFixture[str]) -> None:
    print_json_payload({'ok': True})

    captured = capsys.readouterr()
    assert '{\n  "ok": true\n}' in captured.out



def test_verify_command_uses_runtime_contract_for_powershell_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
        recorded['repo_root'] = repo_root
        return {'coherence_gate': 'scripts/verify/custom-coherence-gate.ps1'}

    def fake_passthrough(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
        recorded['frontend'] = args.frontend
        recorded['shell_script'] = shell_script
        recorded['powershell_script'] = powershell_script
        recorded['rest'] = list(args.rest)
        return 0

    monkeypatch.setattr(cli_commands, 'get_installed_runtime_config', fake_get_installed_runtime_config)
    monkeypatch.setattr(cli_commands, 'passthrough_command', fake_passthrough)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        frontend='powershell',
        rest=['--artifacts'],
    )

    assert verify_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['frontend'] == 'powershell'
    assert recorded['shell_script'] == 'check.sh'
    assert recorded['powershell_script'] == 'scripts/verify/custom-coherence-gate.ps1'
    assert recorded['rest'] == ['--artifacts']


def test_verify_command_rejects_shell_frontend_without_check_fallback(tmp_path: Path) -> None:
    with pytest.raises(
        CliError,
        match="PowerShell-first operator command.*installed locally",
    ):
        verify_command(
            argparse.Namespace(
                repo_root=str(tmp_path),
                frontend='shell',
                rest=[],
            )
        )



def test_runtime_command_uses_runtime_contract_for_powershell_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_get_installed_runtime_config(repo_root: Path) -> dict[str, object]:
        recorded['repo_root'] = repo_root
        return {'runtime_entrypoint': 'scripts/runtime/custom-runtime-entrypoint.ps1'}

    def fake_passthrough(args: argparse.Namespace, *, shell_script: str, powershell_script: str) -> int:
        recorded['frontend'] = args.frontend
        recorded['shell_script'] = shell_script
        recorded['powershell_script'] = powershell_script
        recorded['rest'] = list(args.rest)
        return 0

    monkeypatch.setattr(cli_commands, 'get_installed_runtime_config', fake_get_installed_runtime_config)
    monkeypatch.setattr(cli_commands, 'passthrough_command', fake_passthrough)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        frontend='powershell',
        rest=['--task', 'smoke'],
    )

    assert runtime_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['frontend'] == 'powershell'
    assert recorded['shell_script'] == 'check.sh'
    assert recorded['powershell_script'] == 'scripts/runtime/custom-runtime-entrypoint.ps1'
    assert recorded['rest'] == ['--task', 'smoke']


def test_runtime_command_rejects_shell_frontend_without_check_fallback(tmp_path: Path) -> None:
    with pytest.raises(
        CliError,
        match="PowerShell-first operator command.*runtime coherent",
    ):
        runtime_command(
            argparse.Namespace(
                repo_root=str(tmp_path),
                frontend='shell',
                rest=[],
            )
        )


def test_upgrade_command_aliases_update_with_migration_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_update_command(args: argparse.Namespace) -> int:
        recorded["repo_root"] = args.repo_root
        recorded["skills_dir"] = args.skills_dir
        return 0

    monkeypatch.setattr(cli_commands, "update_command", fake_update_command)

    result = upgrade_command(argparse.Namespace(repo_root='/tmp/repo', skills_dir='/tmp/skills'))

    assert result == 0
    assert recorded == {"repo_root": "/tmp/repo", "skills_dir": "/tmp/skills"}
    assert "deprecated" in capsys.readouterr().err


def test_build_parser_includes_upgrade_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(['upgrade', '--repo-root', '/tmp/repo', '--skills-dir', '/tmp/skills'])

    assert args.command == 'upgrade'
    assert args.handler is upgrade_command
    assert args.skills_dir == '/tmp/skills'
    with pytest.raises(SystemExit):
        parser.parse_args(['upgrade', '--repo-root', '/tmp/repo', '--host', 'codex'])


def test_public_installer_commands_do_not_import_legacy_adapter_install_path() -> None:
    commands_content = (CLI_SRC / "vgo_cli" / "commands.py").read_text(encoding="utf-8")

    forbidden_terms = (
        "run_installer_core",
        "run_uninstaller_core",
        "upgrade_runtime",
        "reconcile_install_postconditions",
        "print_install_banner",
        "print_install_completion_hint",
    )
    for term in forbidden_terms:
        assert term not in commands_content


def test_public_cli_output_does_not_advertise_legacy_adapter_install_commands() -> None:
    output_content = (CLI_SRC / "vgo_cli" / "output.py").read_text(encoding="utf-8")

    forbidden_terms = (
        "-HostId",
        "-Profile",
        "-TargetRoot",
        "--host",
        "--profile",
        "--target-root",
    )
    for term in forbidden_terms:
        assert term not in output_content


def test_build_parser_uses_skills_dir_for_install_and_rejects_old_host_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(['install', '--repo-root', '/tmp/repo', '--skills-dir', '/tmp/skills'])

    assert args.command == 'install'
    assert args.skills_dir == '/tmp/skills'
    assert not hasattr(args, 'host')
    with pytest.raises(SystemExit):
        parser.parse_args(['install', '--repo-root', '/tmp/repo', '--host', 'codex'])


def test_build_parser_uses_skills_dir_for_file_level_installer_commands() -> None:
    parser = build_parser()

    install_args = parser.parse_args(['install', '--repo-root', '/tmp/repo'])
    uninstall_args = parser.parse_args(['uninstall', '--repo-root', '/tmp/repo', '--skills-dir', '/tmp/skills'])
    update_args = parser.parse_args(['update', '--repo-root', '/tmp/repo', '--skills-dir', '/tmp/skills'])
    upgrade_args = parser.parse_args(['upgrade', '--repo-root', '/tmp/repo', '--skills-dir', '/tmp/skills'])

    assert install_args.skills_dir == ''
    assert uninstall_args.skills_dir == '/tmp/skills'
    assert update_args.skills_dir == '/tmp/skills'
    assert upgrade_args.skills_dir == '/tmp/skills'


def test_install_command_uses_simplified_skills_dir_install(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skills_dir = tmp_path / 'skills'
    args = argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))

    assert install_command(args) == 0

    receipt_path = skills_dir / 'vibe' / '.vibeskills' / 'install-receipt.json'
    assert receipt_path.is_file()
    assert (skills_dir / 'vibe' / 'SKILL.md').is_file()
    assert not (skills_dir / 'vibe' / 'adapters').exists()
    assert '"receipt_kind": "vibe-skill-install"' in capsys.readouterr().out


def test_install_command_marks_non_git_source_as_unknown_dirty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'SKILL.md').parent.mkdir(parents=True, exist_ok=True)
    (repo_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    skills_dir = tmp_path / 'skills'

    assert install_command(argparse.Namespace(repo_root=str(repo_root), skills_dir=str(skills_dir))) == 0

    output = capsys.readouterr().out
    assert '"source_git_commit": "unknown"' in output
    assert '"source_git_dirty": true' in output


def test_install_command_uses_public_release_bundle_metadata_when_present(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release_root = tmp_path / 'release-root'
    release_root.mkdir(parents=True, exist_ok=True)
    (release_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    (release_root / 'release-bundle.json').write_text(
        json.dumps(
            {
                'release': {'version': '3.2.0'},
                'asset': {
                    'file_name': 'vibe-skills-3.2.0-public.zip',
                    'payload_digest_sha256': 'bundle-digest-123',
                },
                'public_install': {'source_kind': 'public_release'},
            }
        ),
        encoding='utf-8',
    )
    skills_dir = tmp_path / 'skills'

    assert install_command(argparse.Namespace(repo_root=str(release_root), skills_dir=str(skills_dir))) == 0

    output = capsys.readouterr().out
    assert '"source_kind": "public_release"' in output
    assert '"version": "3.2.0"' in output
    assert '"asset_name": "vibe-skills-3.2.0-public.zip"' in output
    assert '"source_git_commit"' not in output
    assert '"source_git_dirty"' not in output


def test_uninstall_command_uses_simplified_skills_dir_uninstall(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills_dir = tmp_path / 'skills'
    assert install_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0
    capsys.readouterr()

    assert uninstall_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0

    assert not (skills_dir / 'vibe').exists()
    assert '"removed_files"' in capsys.readouterr().out


def test_update_command_uses_simplified_skills_dir_update(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills_dir = tmp_path / 'skills'
    assert install_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0
    capsys.readouterr()

    assert update_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0

    assert (skills_dir / 'vibe' / '.vibeskills' / 'install-receipt.json').is_file()
    assert '"receipt_kind": "vibe-skill-install"' in capsys.readouterr().out


def test_check_command_uses_simplified_skills_dir_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    skills_dir = tmp_path / 'skills'
    assert install_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0
    capsys.readouterr()

    assert check_command(argparse.Namespace(repo_root=str(REPO_ROOT), skills_dir=str(skills_dir))) == 0

    output = capsys.readouterr().out
    assert '"ok": true' in output
    assert '"scope": "installed_vibe_skill"' in output
    assert '"result": "passed"' in output
    assert '"task completion"' in output
    assert '"material skill execution"' in output
    assert '"runtime coherent"' in output
    assert '"delivery accepted"' in output


def test_build_parser_includes_index_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args([
        'index',
        '--repo-root',
        '/tmp/repo',
        '--agent-root',
        '/tmp/agent',
        '--host-id',
        'codex',
        '--workspace-root',
        '/tmp/workspace',
    ])

    assert args.command == 'index'
    assert args.handler is index_command
    assert args.host_id == 'codex'
    assert args.workspace_root == '/tmp/workspace'
    assert args.json is False


def test_build_parser_includes_run_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args([
        'run',
        '--repo-root',
        '/tmp/repo',
        '--agent-root',
        '/tmp/agent',
        '--prompt',
        'review this',
        '--host-id',
        'codex',
        '--workspace-root',
        '/tmp/workspace',
    ])

    assert args.command == 'run'
    assert args.handler is run_command
    assert args.host_id == 'codex'
    assert args.workspace_root == '/tmp/workspace'
    assert args.run_id is None


def test_build_parser_includes_inspect_run_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args([
        'inspect-run',
        '--repo-root',
        '/tmp/repo',
        '--agent-root',
        '/tmp/agent',
        '--run-id',
        'run-1',
        '--host-id',
        'codex',
        '--workspace-root',
        '/tmp/workspace',
    ])

    assert args.command == 'inspect-run'
    assert args.handler is inspect_run_command
    assert args.host_id == 'codex'
    assert args.workspace_root == '/tmp/workspace'
    assert args.run_id == 'run-1'


def test_build_parser_includes_locate_entry_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(['locate-entry', '--repo-root', '/tmp/repo', '--change-kind', 'execution'])

    assert args.command == 'locate-entry'
    assert args.handler is locate_entry_command
    assert args.change_kind == 'execution'


def test_build_parser_accepts_local_skill_extension_locate_entry() -> None:
    parser = build_parser()
    args = parser.parse_args(['locate-entry', '--repo-root', '/tmp/repo', '--change-kind', 'local-skill-extension'])

    assert args.command == 'locate-entry'
    assert args.change_kind == 'local-skill-extension'


def test_build_parser_includes_compatibility_exit_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(['compatibility-exit', '--repo-root', '/tmp/repo'])

    assert args.command == 'compatibility-exit'
    assert args.handler is compatibility_exit_command


def test_build_parser_includes_canonical_entry_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(['canonical-entry', '--repo-root', '/tmp/repo', '--prompt', 'enter canonical vibe'])

    assert args.command == 'canonical-entry'
    assert args.handler is canonical_entry_command
    assert args.host_id == 'codex'
    assert args.entry_id == 'vibe'


def test_build_parser_accepts_canonical_entry_host_decision_json_file() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'canonical-entry',
            '--repo-root',
            '/tmp/repo',
            '--prompt',
            'continue canonical vibe',
            '--host-decision-json-file',
            '/tmp/decision.json',
        ]
    )

    assert args.command == 'canonical-entry'
    assert args.host_decision_json_file == '/tmp/decision.json'


def test_build_parser_accepts_canonical_entry_local_agent_root() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'canonical-entry',
            '--repo-root',
            '/tmp/repo',
            '--prompt',
            'continue canonical vibe',
            '--local-agent-root',
            '/tmp/agent-root',
        ]
    )

    assert args.command == 'canonical-entry'
    assert args.local_agent_root == '/tmp/agent-root'


def test_build_parser_accepts_legacy_wrapper_metadata_flag_for_canonical_entry() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'canonical-entry',
            '--repo-root',
            '/tmp/repo',
            '--prompt',
            'enter canonical vibe',
            '--allow-public-grade-flags',
            'false',
        ]
    )

    assert args.command == 'canonical-entry'
    assert args.allow_public_grade_flags == 'false'


def test_build_parser_rejects_old_install_external_flag() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(['install', '--repo-root', '/tmp/repo', '--install-external'])
