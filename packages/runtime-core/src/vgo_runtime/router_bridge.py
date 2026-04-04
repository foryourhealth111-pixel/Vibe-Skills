#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .router_contract_runtime import route_prompt
from .router_contract_support import resolve_repo_root


def resolve_powershell_host() -> str | None:
    candidates = [
        shutil.which('pwsh'),
        shutil.which('pwsh.exe'),
        shutil.which('powershell'),
        shutil.which('powershell.exe'),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def invoke_canonical_router(args: argparse.Namespace, shell: str) -> dict:
    repo_root = resolve_repo_root(Path(__file__))
    script_path = repo_root / 'scripts' / 'router' / 'resolve-pack-route.ps1'
    command = [
        shell,
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        str(script_path),
        '-Prompt',
        args.prompt,
        '-Grade',
        args.grade,
        '-TaskType',
        args.task_type,
    ]
    if args.requested_skill:
        command.extend(['-RequestedSkill', args.requested_skill])
    if args.host_id:
        command.extend(['-HostId', args.host_id])
    if args.target_root:
        command.extend(['-TargetRoot', args.target_root])
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Host-neutral VCO router entrypoint.')
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--grade', default='M', choices=['M', 'L', 'XL'])
    parser.add_argument('--task-type', default='planning', choices=['planning', 'coding', 'review', 'debug', 'research'])
    parser.add_argument('--requested-skill')
    parser.add_argument('--host-id')
    parser.add_argument('--target-root')
    parser.add_argument('--force-runtime-neutral', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    shell = None if args.force_runtime_neutral else resolve_powershell_host()

    if shell:
        payload = invoke_canonical_router(args, shell)
    else:
        payload = route_prompt(
            prompt=args.prompt,
            grade=args.grade,
            task_type=args.task_type,
            requested_skill=args.requested_skill,
            target_root=args.target_root,
            host_id=args.host_id,
            repo_root=resolve_repo_root(Path(__file__)),
        )

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
