from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


EXPECTED_FILES = [
    'skills/vibe/SKILL.md',
    'skills/brainstorming/SKILL.md',
    '.vibeskills/host-settings.json',
    '.vibeskills/host-closure.json',
    'opencode.json.example',
]


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    return {
        'cmd': cmd,
        'cwd': str(cwd),
        'returncode': completed.returncode,
        'stdout': completed.stdout,
        'stderr': completed.stderr,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def detect_skill_hit(stdout: str) -> bool:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, list):
        for entry in payload:
            if isinstance(entry, dict) and (
                entry.get('name') == 'vibe'
                or str(entry.get('location') or '').endswith('/skills/vibe/SKILL.md')
            ):
                return True

    return ('"name": "vibe"' in stdout) or ('skills/vibe/SKILL.md' in stdout)


def skill_output_looks_truncated(stdout: str) -> bool:
    stripped = stdout.rstrip()
    return stripped.startswith('[') and not stripped.endswith(']')


def build_real_opencode_config(_target_root: Path) -> dict[str, Any]:
    return {
        '$schema': 'https://opencode.ai/config.json',
        'mcp': {
            'playwright': {
                'enabled': True,
                'type': 'local',
                'command': ['npx', '@playwright/mcp@latest'],
            }
        },
    }
