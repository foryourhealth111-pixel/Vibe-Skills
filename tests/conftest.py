from __future__ import annotations

import os
import shutil
import sys

from _python_source_roots import PYTHON_SOURCE_ROOTS, REPO_ROOT


PYCACHE_ROOT = REPO_ROOT / ".tmp" / "pycache"

# Keep pytest runs hermetic for repo-owned Python sources.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("PYTHONPYCACHEPREFIX", str(PYCACHE_ROOT))
sys.dont_write_bytecode = True
sys.pycache_prefix = str(PYCACHE_ROOT)

for root in PYTHON_SOURCE_ROOTS:
    if not root.exists():
        continue
    for cache_dir in root.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
    for artifact in root.rglob("*.pyc"):
        artifact.unlink(missing_ok=True)
    for artifact in root.rglob("*.pyo"):
        artifact.unlink(missing_ok=True)
