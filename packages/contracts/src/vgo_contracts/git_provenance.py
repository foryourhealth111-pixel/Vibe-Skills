from __future__ import annotations

import os
from pathlib import Path
import subprocess


def source_git_text(repo_root: Path, *args: str) -> str:
    """Query only this source's Git metadata, independent of caller repository state."""
    if not (repo_root / ".git").exists():
        raise FileNotFoundError(f"Source has no local Git metadata: {repo_root}")
    env = os.environ.copy()
    for name in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
        "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE",
        "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
        "GIT_SHALLOW_FILE", "GIT_COMMON_DIR", "GIT_NAMESPACE",
    ):
        env.pop(name, None)
    return subprocess.run(
        ["git", "--git-dir=.git", "--work-tree=.", *args],
        cwd=repo_root, env=env, capture_output=True, text=True, check=True, timeout=10,
    ).stdout.strip()
