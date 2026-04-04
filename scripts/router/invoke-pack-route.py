#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if CLI_SRC.is_dir() and str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.main import main


if __name__ == '__main__':
    raise SystemExit(main(['route', '--repo-root', str(REPO_ROOT), *sys.argv[1:]]))
