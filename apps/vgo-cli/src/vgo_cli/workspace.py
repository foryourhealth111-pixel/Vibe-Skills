from __future__ import annotations

import sys
from pathlib import Path


def extend_workspace_package_path(repo_root: Path) -> None:
    for rel in ('packages/contracts/src', 'packages/installer-core/src', 'packages/runtime-core/src'):
        src = repo_root / rel
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
