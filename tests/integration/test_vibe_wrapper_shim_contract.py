from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compatibility_wrapper_shims_require_launch_before_proof_validation() -> None:
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
        content = path.read_text(encoding="utf-8")
        assert "Launch canonical-entry first" in content, path.as_posix()
        assert "do not preflight-scan the current workspace or repository for canonical proof files before launch" in content, path.as_posix()
        if "commands" in path.parts:
            assert "Validate canonical receipts only after canonical-entry returns a session root." in content, path.as_posix()
        else:
            assert "Launch canonical-entry first; validate receipts only after it returns a session root" in content, path.as_posix()
