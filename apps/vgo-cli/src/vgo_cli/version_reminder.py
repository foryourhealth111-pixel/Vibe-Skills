from __future__ import annotations

import argparse
from pathlib import Path
import sys


if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vgo_cli.upgrade_service import has_recorded_install_truth, load_recorded_install_status, refresh_upstream_status
from vgo_cli.upgrade_state import is_upstream_cache_stale


def build_update_reminder(repo_root: Path, target_root: Path, host_id: str) -> str | None:
    try:
        status = load_recorded_install_status(repo_root, target_root, host_id)
        if not has_recorded_install_truth(status):
            return None
        if is_upstream_cache_stale(status):
            status = refresh_upstream_status(repo_root, target_root, status)
    except Exception:
        return None

    if not bool(status.get('update_available')):
        return None

    local_version = str(status.get('installed_version') or 'unknown')
    local_commit = str(status.get('installed_commit') or 'unknown')
    remote_version = str(status.get('remote_latest_version') or 'unknown')
    remote_commit = str(status.get('remote_latest_commit') or 'unknown')
    normalized_host = str(host_id or 'unknown').strip() or 'unknown'
    return (
        '[INFO] Vibe-Skills update available: '
        f'local={local_version}@{local_commit} '
        f'latest={remote_version}@{remote_commit}. '
        f'Run vibe-upgrade --host={normalized_host}.'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--target-root', required=True)
    parser.add_argument('--host', required=True)
    args = parser.parse_args(argv)

    message = build_update_reminder(Path(args.repo_root).resolve(), Path(args.target_root).resolve(), str(args.host))
    if message:
        print(message)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
