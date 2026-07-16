from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPERS = (
    REPO_ROOT
    / "packages"
    / "installer-core"
    / "src"
    / "vgo_installer"
    / "discoverable_wrappers.py"
)


def test_generated_wrappers_preserve_the_current_task_on_launch_and_reentry() -> None:
    text = WRAPPERS.read_text(encoding="utf-8")

    assert "current user task verbatim" in text
    assert "Do not summarize, rewrite, or reduce it to keywords" in text
    assert text.count('--prompt "$VIBE_TASK"') == 2
    assert 'continue approved governed requirement with prior task context' not in text
