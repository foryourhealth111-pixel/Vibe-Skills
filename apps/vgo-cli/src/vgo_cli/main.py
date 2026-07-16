from __future__ import annotations

import argparse
import sys

from .commands import canonical_entry_command, check_command, compatibility_exit_command, index_command, inspect_run_command, install_command, locate_entry_command, passthrough_command, route_command, run_command, runtime_command, uninstall_command, update_command, upgrade_command, verify_command
from .errors import CliError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    install_parser = subparsers.add_parser(
        'install',
        help='Install Vibe into a skills directory from the current source or an extracted public release copy.',
    )
    install_parser.add_argument('--repo-root', required=True)
    install_parser.add_argument('--skills-dir', default='')
    install_parser.set_defaults(handler=install_command)

    uninstall_parser = subparsers.add_parser('uninstall')
    uninstall_parser.add_argument('--repo-root', required=True)
    uninstall_parser.add_argument('--skills-dir', default='')
    uninstall_parser.set_defaults(handler=uninstall_command)

    update_parser = subparsers.add_parser(
        'update',
        help='Update an installed Vibe copy from the current source or an extracted newer public release copy.',
    )
    update_parser.add_argument('--repo-root', required=True)
    update_parser.add_argument('--skills-dir', default='')
    update_parser.set_defaults(handler=update_command)

    upgrade_parser = subparsers.add_parser('upgrade', help='Compatibility alias for update.')
    upgrade_parser.add_argument('--repo-root', required=True)
    upgrade_parser.add_argument('--skills-dir', default='')
    upgrade_parser.set_defaults(handler=upgrade_command)

    index_parser = subparsers.add_parser('index')
    index_parser.add_argument('--repo-root', required=True)
    index_parser.add_argument('--agent-root', required=True)
    index_parser.add_argument('--host-id')
    index_parser.add_argument('--workspace-root')
    index_parser.add_argument('--json', action='store_true')
    index_parser.set_defaults(handler=index_command)

    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('--repo-root', required=True)
    run_parser.add_argument('--agent-root', required=True)
    run_parser.add_argument('--prompt', required=True)
    run_parser.add_argument('--run-id')
    run_parser.add_argument('--host-id')
    run_parser.add_argument('--workspace-root')
    run_parser.add_argument('--json', action='store_true')
    run_parser.set_defaults(handler=run_command)

    inspect_run_parser = subparsers.add_parser('inspect-run')
    inspect_run_parser.add_argument('--repo-root', required=True)
    inspect_run_parser.add_argument('--agent-root', required=True)
    inspect_run_parser.add_argument('--run-id', required=True)
    inspect_run_parser.add_argument('--host-id')
    inspect_run_parser.add_argument('--workspace-root')
    inspect_run_parser.set_defaults(handler=inspect_run_command)

    locate_entry_parser = subparsers.add_parser('locate-entry')
    locate_entry_parser.add_argument('--repo-root', required=True)
    locate_entry_parser.add_argument('--change-kind', required=True, choices=('task-understanding', 'planning', 'execution', 'verification', 'local-skill-extension'))
    locate_entry_parser.set_defaults(handler=locate_entry_command)

    compatibility_exit_parser = subparsers.add_parser('compatibility-exit')
    compatibility_exit_parser.add_argument('--repo-root', required=True)
    compatibility_exit_parser.set_defaults(handler=compatibility_exit_command)

    route_parser = subparsers.add_parser('route')
    route_parser.add_argument('--repo-root', required=True)
    route_parser.add_argument('--prompt', required=True)
    route_parser.add_argument('--grade', default='M', choices=('M', 'L', 'XL'))
    route_parser.add_argument('--task-type', default='planning', choices=('planning', 'coding', 'review', 'debug', 'research'))
    route_parser.add_argument('--requested-skill')
    route_parser.add_argument('--host-id')
    route_parser.add_argument('--target-root')
    route_parser.add_argument('--output-json-path')
    route_parser.add_argument('--force-runtime-neutral', action='store_true')
    route_parser.set_defaults(handler=route_command)

    canonical_entry_parser = subparsers.add_parser('canonical-entry')
    canonical_entry_parser.add_argument('--repo-root', required=True)
    canonical_entry_parser.add_argument('--host-id', default=None, help=argparse.SUPPRESS)
    canonical_entry_parser.add_argument('--entry-id', default=None, help=argparse.SUPPRESS)
    canonical_entry_parser.add_argument('--prompt', required=True)
    canonical_entry_parser.add_argument('--requested-stage-stop')
    canonical_entry_parser.add_argument('--requested-grade-floor', choices=('L', 'XL'))
    canonical_entry_parser.add_argument('--run-id')
    canonical_entry_parser.add_argument('--workspace-root', help=argparse.SUPPRESS)
    canonical_entry_parser.add_argument('--artifact-root')
    canonical_entry_parser.add_argument('--local-agent-root')
    canonical_entry_parser.add_argument('--continue-from-run-id')
    canonical_entry_parser.add_argument('--bounded-reentry-token')
    canonical_entry_parser.add_argument('--module-execution-json-file')
    canonical_entry_parser.add_argument('--host-decision-json')
    canonical_entry_parser.add_argument('--host-decision-json-file')
    canonical_entry_parser.add_argument('--force-runtime-neutral', action='store_true')
    canonical_entry_parser.add_argument('--allow-public-grade-flags', nargs='?', const='true', help=argparse.SUPPRESS)
    canonical_entry_parser.set_defaults(handler=canonical_entry_command)

    check_parser = subparsers.add_parser(
        'check',
        help='Verify the installed vibe skill receipt and owned files.',
        description='Prove only that the installed vibe skill is present and matches its install receipt.',
    )
    check_parser.add_argument('--repo-root', required=True)
    check_parser.add_argument('--skills-dir', default='')
    check_parser.set_defaults(handler=check_command)

    verify_parser = subparsers.add_parser(
        'verify',
        help='PowerShell-only operator entry for runtime coherence / release audit gates.',
        description='Run the PowerShell coherence gate. This is not the public install proof command.',
    )
    verify_parser.add_argument('--repo-root', required=True)
    verify_parser.add_argument('--frontend', choices=('shell', 'powershell'), default='powershell')
    verify_parser.add_argument('rest', nargs=argparse.REMAINDER)
    verify_parser.set_defaults(handler=verify_command)

    runtime_parser = subparsers.add_parser(
        'runtime',
        help='PowerShell-only operator entry for the governed runtime script.',
        description='Run the PowerShell governed runtime entrypoint. This is not the install proof command.',
    )
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
