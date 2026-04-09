from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
RUNTIME_SRC = REPO_ROOT / 'packages' / 'runtime-core' / 'src'
for src in (CLI_SRC, RUNTIME_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_cli.commands import install_command, route_command, runtime_command, upgrade_command, verify_command
from vgo_cli.errors import CliError
from vgo_cli.main import build_parser
from vgo_cli.output import parse_json_output, print_install_completion_hint, print_json_payload
from vgo_runtime import router_bridge


def test_parse_json_output_returns_payload() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='{"ok": true}', stderr='')

    assert parse_json_output(result) == {'ok': True}


def test_parse_json_output_rejects_invalid_json() -> None:
    result = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='not-json', stderr='')

    with pytest.raises(CliError, match='Invalid JSON output from core command'):
        parse_json_output(result)


def test_print_install_completion_hint_for_shell_includes_host(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    print_install_completion_hint('shell', host_id='cursor', profile='full', target_root=tmp_path)

    captured = capsys.readouterr()
    assert f'Install done. Run: bash check.sh --profile full --host cursor --target-root {tmp_path}' in captured.out


def test_print_install_completion_hint_for_powershell_includes_host(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    print_install_completion_hint('powershell', host_id='cursor', profile='full', target_root=tmp_path)

    captured = capsys.readouterr()
    assert '-HostId cursor' in captured.out
    assert f'-TargetRoot {tmp_path}' in captured.out


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
        requested_skill='vibe-how',
        entry_intent_id='vibe-how',
        requested_grade_floor='XL',
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
        '--requested-skill', 'vibe-how',
        '--entry-intent-id', 'vibe-how',
        '--requested-grade-floor', 'XL',
        '--host-id', 'codex',
        '--target-root', '/tmp/codex',
        '--force-runtime-neutral',
    ]
    assert recorded['printed_stdout'] == '{"ok": true}\n'


def test_router_bridge_forwards_discoverable_flags_to_powershell_router(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded['command'] = list(command)
        recorded['cwd'] = kwargs['cwd']
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout='{"ok": true}\n', stderr='')

    monkeypatch.setattr(router_bridge, 'resolve_repo_root', lambda _: tmp_path)
    monkeypatch.setattr(router_bridge.subprocess, 'run', fake_run)

    payload = router_bridge.invoke_canonical_router(
        argparse.Namespace(
            prompt='route this',
            grade='XL',
            task_type='debug',
            requested_skill='vibe-how',
            entry_intent_id='vibe-how',
            requested_grade_floor='XL',
            host_id='codex',
            target_root='/tmp/codex',
        ),
        'pwsh',
    )

    assert payload == {'ok': True}
    assert recorded['cwd'] == tmp_path
    assert recorded['command'] == [
        'pwsh',
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        str(tmp_path / 'scripts' / 'router' / 'resolve-pack-route.ps1'),
        '-Prompt',
        'route this',
        '-Grade',
        'XL',
        '-TaskType',
        'debug',
        '-RequestedSkill',
        'vibe-how',
        '-EntryIntentId',
        'vibe-how',
        '-RequestedGradeFloor',
        'XL',
        '-HostId',
        'codex',
        '-TargetRoot',
        '/tmp/codex',
    ]


def test_router_bridge_runtime_neutral_fallback_passes_discoverable_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorded: dict[str, object] = {}

    def fake_route_prompt(**kwargs: object) -> dict[str, object]:
        recorded.update(kwargs)
        return {'ok': True}

    monkeypatch.setattr(router_bridge, 'resolve_powershell_host', lambda: None)
    monkeypatch.setattr(router_bridge, 'resolve_repo_root', lambda _: tmp_path)
    monkeypatch.setattr(router_bridge, 'route_prompt', fake_route_prompt)

    assert (
        router_bridge.main(
            [
                '--prompt',
                'route this',
                '--grade',
                'XL',
                '--task-type',
                'debug',
                '--requested-skill',
                'vibe-how',
                '--entry-intent-id',
                'vibe-how',
                '--requested-grade-floor',
                'XL',
                '--host-id',
                'codex',
                '--target-root',
                '/tmp/codex',
                '--force-runtime-neutral',
            ]
        )
        == 0
    )

    assert recorded == {
        'prompt': 'route this',
        'grade': 'XL',
        'task_type': 'debug',
        'requested_skill': 'vibe-how',
        'entry_intent_id': 'vibe-how',
        'requested_grade_floor': 'XL',
        'target_root': '/tmp/codex',
        'host_id': 'codex',
        'repo_root': tmp_path,
    }
    assert capsys.readouterr().out == '{\n  "ok": true\n}\n'



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


def test_install_command_skips_external_dependency_install_when_strict_offline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_normalize_host_id(host: str) -> str:
        return host

    def fake_resolve_target_root(host_id: str, target_root: str | None) -> Path:
        recorded['resolved_host'] = host_id
        return Path(target_root or tmp_path / 'target').resolve()

    def fake_assert_target_root_matches_host_intent(target_root: Path, host_id: str) -> None:
        recorded['intent_checked'] = (target_root, host_id)

    def fake_install_mode_for_host(host_id: str) -> str:
        return 'preview-guidance'

    def fake_run_installer_core(repo_root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        recorded['installer_repo_root'] = repo_root
        recorded['installer_argv'] = list(argv)
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=0,
            stdout='{"install_mode":"preview-guidance","external_fallback_used":[]}\n',
            stderr='',
        )

    def fake_reconcile_install_postconditions(
        repo_root: Path,
        target_root: Path,
        host_id: str,
        **kwargs: object,
    ) -> dict[str, object]:
        recorded['reconcile'] = {
            'repo_root': repo_root,
            'target_root': target_root,
            'host_id': host_id,
            **kwargs,
        }
        return {'install_receipt': {}, 'mcp_receipt': {}}

    def fake_maybe_install_external_dependencies(repo_root: Path, install_mode: str, *, strict_offline: bool = False) -> None:
        recorded['external_called'] = {
            'repo_root': repo_root,
            'install_mode': install_mode,
            'strict_offline': strict_offline,
        }

    monkeypatch.setattr(cli_commands, 'normalize_host_id', fake_normalize_host_id)
    monkeypatch.setattr(cli_commands, 'resolve_target_root', fake_resolve_target_root)
    monkeypatch.setattr(cli_commands, 'assert_target_root_matches_host_intent', fake_assert_target_root_matches_host_intent)
    monkeypatch.setattr(cli_commands, 'install_mode_for_host', fake_install_mode_for_host)
    monkeypatch.setattr(cli_commands, 'run_installer_core', fake_run_installer_core)
    monkeypatch.setattr(cli_commands, 'reconcile_install_postconditions', fake_reconcile_install_postconditions)
    monkeypatch.setattr(cli_commands, 'maybe_install_external_dependencies', fake_maybe_install_external_dependencies)
    monkeypatch.setattr(cli_commands, 'print_install_banner', lambda *args, **kwargs: None)
    monkeypatch.setattr(cli_commands, 'print_install_completion_hint', lambda *args, **kwargs: None)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        host='cursor',
        target_root=str(tmp_path / 'target'),
        profile='full',
        require_closed_ready=False,
        allow_external_skill_fallback=False,
        install_external=True,
        strict_offline=True,
        skip_runtime_freshness_gate=False,
        frontend='shell',
    )

    assert install_command(args) == 0
    assert 'external_called' not in recorded
    assert recorded['reconcile']['strict_offline'] is True


def test_build_parser_exposes_upgrade_subcommand() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            'upgrade',
            '--repo-root',
            '/tmp/repo',
            '--host',
            'codex',
        ]
    )

    assert args.command == 'upgrade'
    assert args.host == 'codex'
    assert args.handler is upgrade_command


def test_upgrade_command_delegates_to_upgrade_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import vgo_cli.commands as cli_commands

    recorded: dict[str, object] = {}

    def fake_upgrade_runtime(**kwargs: object) -> dict[str, object]:
        recorded.update(kwargs)
        return {'changed': False}

    monkeypatch.setattr(cli_commands, 'upgrade_runtime', fake_upgrade_runtime)

    args = argparse.Namespace(
        repo_root=str(tmp_path),
        frontend='shell',
        profile='full',
        host='codex',
        target_root='',
        install_external=False,
        strict_offline=False,
        require_closed_ready=False,
        allow_external_skill_fallback=False,
        skip_runtime_freshness_gate=False,
    )

    assert upgrade_command(args) == 0
    assert recorded['repo_root'] == tmp_path.resolve()
    assert recorded['host_id'] == 'codex'
    assert recorded['profile'] == 'full'
    assert recorded['frontend'] == 'shell'
