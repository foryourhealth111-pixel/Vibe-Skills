#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRCS = (
    REPO_ROOT / 'packages' / 'contracts' / 'src',
    REPO_ROOT / 'packages' / 'installer-core' / 'src',
)
for src in reversed(PACKAGE_SRCS):
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.install_runtime import main, uses_skill_only_activation


if __name__ == '__main__':
    raise SystemExit(main())
