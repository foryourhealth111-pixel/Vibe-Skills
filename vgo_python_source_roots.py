from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
PYTHON_SOURCE_ROOTS = (
    REPO_ROOT / "apps",
    REPO_ROOT / "packages",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
)

__all__ = ["PYTHON_SOURCE_ROOTS", "REPO_ROOT"]
