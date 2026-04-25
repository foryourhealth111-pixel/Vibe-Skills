from __future__ import annotations

import argparse
import sys

from .commands import canonical_entry_command, install_command, passthrough_command, route_command, runtime_command, uninstall_command, upgrade_command, verify_command
from .errors import CliError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--repo-root', required=True)
    install_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    install_parser.add_argument('--profile', choices=('minimal', 'full'), default='full')
    install_parser.add_argument('--host', default='codex')
    install_parser.add_argument('--target-root', default='')
    install_parser.add_argument('--install-external', action='store_true')
    install_parser.add_argument('--strict-offline', action='store_true')
    install_parser.add_argument('--require-closed-ready', action='store_true')
    install_parser.add_argument('--allow-external-skill-fallback', action='store_true')
    install_parser.add_argument('--skip-runtime-freshness-gate', action='store_true')
    install_parser.set_defaults(handler=install_command)

    uninstall_parser = subparsers.add_parser('uninstall')
    uninstall_parser.add_argument('--repo-root', required=True)
    uninstall_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    uninstall_parser.add_argument('--profile', choices=('minimal', 'full'), default='full')
    uninstall_parser.add_argument('--host', default='codex')
    uninstall_parser.add_argument('--target-root', default='')
    uninstall_parser.add_argument('--preview', action='store_true')
    uninstall_parser.add_argument('--purge-empty-dirs', action='store_true')
    uninstall_parser.add_argument('--strict-owned-only', action='store_true')
    uninstall_parser.set_defaults(handler=uninstall_command)

    upgrade_parser = subparsers.add_parser('upgrade')
    upgrade_parser.add_argument('--repo-root', required=True)
    upgrade_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    upgrade_parser.add_argument('--profile', choices=('minimal', 'full'), default='full')
    upgrade_parser.add_argument('--host', default='codex')
    upgrade_parser.add_argument('--target-root', default='')
    upgrade_parser.add_argument('--install-external', action='store_true')
    upgrade_parser.add_argument('--strict-offline', action='store_true')
    upgrade_parser.add_argument('--require-closed-ready', action='store_true')
    upgrade_parser.add_argument('--allow-external-skill-fallback', action='store_true')
    upgrade_parser.add_argument('--skip-runtime-freshness-gate', action='store_true')
    upgrade_parser.set_defaults(handler=upgrade_command)

    route_parser = subparsers.add_parser('route')
    route_parser.add_argument('--repo-root', required=True)
    route_parser.add_argument('--prompt', required=True)
    route_parser.add_argument('--grade', default='M', choices=('M', 'L', 'XL'))
    route_parser.add_argument('--task-type', default='planning', choices=('planning', 'coding', 'review', 'debug', 'research'))
    route_parser.add_argument('--requested-skill')
    route_parser.add_argument('--host-id')
    route_parser.add_argument('--target-root')
    route_parser.add_argument('--force-runtime-neutral', action='store_true')
    route_parser.set_defaults(handler=route_command)

    canonical_entry_parser = subparsers.add_parser('canonical-entry')
    canonical_entry_parser.add_argument('--repo-root', required=True)
    canonical_entry_parser.add_argument('--host-id', default='codex')
    canonical_entry_parser.add_argument('--entry-id', default='vibe')
    canonical_entry_parser.add_argument('--prompt', required=True)
    canonical_entry_parser.add_argument('--requested-stage-stop')
    canonical_entry_parser.add_argument('--requested-grade-floor', choices=('L', 'XL'))
    canonical_entry_parser.add_argument('--run-id')
    canonical_entry_parser.add_argument('--artifact-root')
    canonical_entry_parser.add_argument('--continue-from-run-id')
    canonical_entry_parser.add_argument('--bounded-reentry-token')
    canonical_entry_parser.add_argument('--host-decision-json')
    canonical_entry_parser.add_argument('--force-runtime-neutral', action='store_true')
    canonical_entry_parser.add_argument('--allow-public-grade-flags', nargs='?', const='true', help=argparse.SUPPRESS)
    canonical_entry_parser.set_defaults(handler=canonical_entry_command)

    check_parser = subparsers.add_parser('check')
    check_parser.add_argument('--repo-root', required=True)
    check_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='shell')
    check_parser.add_argument('rest', nargs=argparse.REMAINDER)
    check_parser.set_defaults(handler=lambda ns: passthrough_command(ns, shell_script='check.sh', powershell_script='check.ps1'))

    verify_parser = subparsers.add_parser('verify')
    verify_parser.add_argument('--repo-root', required=True)
    verify_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='powershell')
    verify_parser.add_argument('rest', nargs=argparse.REMAINDER)
    verify_parser.set_defaults(handler=verify_command)

    runtime_parser = subparsers.add_parser('runtime')
    runtime_parser.add_argument('--repo-root', required=True)
    runtime_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='powershell')
    runtime_parser.add_argument('rest', nargs=argparse.REMAINDER)
    runtime_parser.set_defaults(handler=runtime_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except CliError as exc:
        message = str(exc).strip()
        if message:
            for line in message.splitlines():
                print(f'[FAIL] {line}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
