#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from .uninstall_service import apply_uninstall, resolve_adapter, uses_skill_only_activation, write_json


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--profile", choices=("minimal", "full"), default="full")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--purge-empty-dirs", action="store_true")
    parser.add_argument("--strict-owned-only", action="store_true", default=True)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    target_root = Path(args.target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    adapter = resolve_adapter(repo_root, args.host)
    payload = apply_uninstall(
        repo_root,
        target_root,
        adapter,
        preview=bool(args.preview),
        purge_empty=bool(args.purge_empty_dirs),
    )
    write_json(payload)


if __name__ == "__main__":
    main()
