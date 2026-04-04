from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .opencode_preview_smoke_support import (
    EXPECTED_FILES,
    build_real_opencode_config,
    detect_skill_hit,
    run,
    skill_output_looks_truncated,
    write_json,
)


def _probe_opencode_cli(repo_root: Path, tmp_root: Path, target_root: Path, repaired_real_config: Any) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    opencode_cli = shutil.which('opencode')
    cli_probe: dict[str, Any] = {
        'present': bool(opencode_cli),
        'binary': opencode_cli,
        'real_config_after_install': repaired_real_config,
        'debug_paths': None,
        'debug_config': None,
        'debug_skill_detects_vibe': None,
        'debug_agent_detects_vibe_plan': None,
        'notes': [],
    }

    if not opencode_cli:
        return failures, warnings, cli_probe

    env = os.environ.copy()
    env['HOME'] = str(tmp_root)
    env['XDG_CONFIG_HOME'] = str(tmp_root / '.config')
    env['XDG_DATA_HOME'] = str(tmp_root / '.local' / 'share')
    env['XDG_STATE_HOME'] = str(tmp_root / '.local' / 'state')
    env['XDG_CACHE_HOME'] = str(tmp_root / '.cache')

    debug_paths = run([opencode_cli, 'debug', 'paths'], cwd=repo_root, env=env)
    cli_probe['debug_paths'] = debug_paths
    if debug_paths['returncode'] != 0:
        failures.append('opencode debug paths failed in isolated env')

    debug_config = run([opencode_cli, 'debug', 'config'], cwd=repo_root, env=env)
    cli_probe['debug_config'] = debug_config
    if debug_config['returncode'] != 0:
        failures.append('opencode debug config failed in isolated env after preview install')

    debug_skill = run([opencode_cli, 'debug', 'skill', '--pure'], cwd=repo_root, env=env)
    cli_probe['debug_skill'] = debug_skill
    skill_hits = detect_skill_hit(debug_skill['stdout'])
    cli_probe['debug_skill_detects_vibe'] = skill_hits
    if debug_skill['returncode'] != 0:
        failures.append('opencode debug skill failed in isolated env')
    if not skill_hits:
        warning = 'opencode debug skill --pure did not enumerate the installed vibe skill in the isolated OpenCode root'
        if skill_output_looks_truncated(debug_skill['stdout']):
            warning += ' (CLI output appears truncated)'
            cli_probe['notes'].append(
                'OpenCode debug skill can emit truncated skill dumps when many skills are installed; debug config and debug agent remain the authoritative startup proof surfaces.'
            )
            warnings.append(warning)
        else:
            failures.append(warning)

    debug_agent = run([opencode_cli, 'debug', 'agent', 'vibe-plan'], cwd=repo_root, env=env)
    cli_probe['debug_agent_detects_vibe_plan'] = debug_agent['returncode'] == 0 and 'vibe-plan' in (debug_agent['stdout'] + debug_agent['stderr'])
    if not cli_probe['debug_agent_detects_vibe_plan']:
        cli_probe['notes'].append('OpenCode preview guidance is sidecar-first; custom agent discovery is advisory until the host natively surfaces preview agents again.')
    cli_probe['debug_agent'] = debug_agent
    return failures, warnings, cli_probe


def evaluate_opencode_preview(repo_root: Path, write_artifacts: bool = False) -> dict[str, Any]:
    install_sh = repo_root / 'install.sh'
    check_sh = repo_root / 'check.sh'
    artifact_path = repo_root / 'outputs' / 'verify' / 'opencode-preview-smoke.json'

    failures: list[str] = []
    warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix='vgo-opencode-preview-') as tmp:
        tmp_root = Path(tmp)
        target_root = tmp_root / '.config' / 'opencode'
        target_root.mkdir(parents=True, exist_ok=True)
        real_config_path = target_root / 'opencode.json'
        write_json(real_config_path, build_real_opencode_config(target_root))

        install_result = run(
            ['bash', str(install_sh), '--host', 'opencode', '--target-root', str(target_root)],
            cwd=repo_root,
            env=os.environ.copy(),
        )
        if install_result['returncode'] != 0:
            failures.append('install.sh --host opencode failed')

        check_result = run(
            ['bash', str(check_sh), '--host', 'opencode', '--target-root', str(target_root)],
            cwd=repo_root,
            env=os.environ.copy(),
        )
        if check_result['returncode'] != 0:
            failures.append('check.sh --host opencode failed')

        missing_files = [rel for rel in EXPECTED_FILES if not (target_root / rel).exists()]
        if missing_files:
            failures.append('expected preview payload missing')

        repaired_real_config = None
        if not real_config_path.exists():
            failures.append('preview install removed the real opencode.json instead of repairing it')
        else:
            try:
                repaired_real_config = json.loads(real_config_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                failures.append('preview install left a non-parseable real opencode.json')
            else:
                if 'vibeskills' in repaired_real_config:
                    failures.append('preview install injected a vibeskills node into the host-managed opencode.json')
                if 'mcp' not in repaired_real_config:
                    failures.append('preview install did not preserve host-managed mcp settings in the real opencode.json')

        cli_failures, cli_warnings, cli_probe = _probe_opencode_cli(
            repo_root=repo_root,
            tmp_root=tmp_root,
            target_root=target_root,
            repaired_real_config=repaired_real_config,
        )
        failures.extend(cli_failures)
        warnings.extend(cli_warnings)

        payload = {
            'gate': 'opencode-preview-smoke',
            'result': 'PASS' if not failures else 'FAIL',
            'repo_root': str(repo_root),
            'target_root': str(target_root),
            'expected_files': EXPECTED_FILES,
            'missing_files': missing_files,
            'install': install_result,
            'check': check_result,
            'opencode_cli': cli_probe,
            'failures': failures,
            'warnings': warnings,
        }

        if write_artifacts:
            write_json(artifact_path, payload)

        return payload
