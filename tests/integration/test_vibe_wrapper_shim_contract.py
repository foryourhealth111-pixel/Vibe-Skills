from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_retired_wrapper_shims_are_removed_from_repo() -> None:
    targets = [
        REPO_ROOT / "bundled" / "skills" / "vibe-what-do-i-want" / "SKILL.md",
        REPO_ROOT / "bundled" / "skills" / "vibe-how-do-we-do" / "SKILL.md",
        REPO_ROOT / "bundled" / "skills" / "vibe-do-it" / "SKILL.md",
        REPO_ROOT / "bundled" / "skills" / "vibe-upgrade" / "SKILL.md",
        REPO_ROOT / "commands" / "vibe-what-do-i-want.md",
        REPO_ROOT / "commands" / "vibe-how-do-we-do.md",
        REPO_ROOT / "commands" / "vibe-do-it.md",
    ]

    for path in targets:
        assert not path.exists(), path.as_posix()
