from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _public_entry_ids() -> set[str]:
    payload = json.loads(_read("config/vibe-entry-surfaces.json"))
    return {
        entry["id"]
        for entry in payload["entries"]
        if entry.get("publicly_exposed") is True
    }


def test_readmes_describe_only_public_vibe_entry_surface() -> None:
    assert _public_entry_ids() == {"vibe", "vibe-upgrade"}

    for path in ("README.md", "README.zh.md", "docs/quick-start.en.md", "docs/quick-start.md"):
        content = _read(path)
        assert "vibe-upgrade" in content
        assert "host-rendered" not in content
        assert "宿主渲染标签" not in content
        for legacy_alias in ("vibe-want", "vibe-how", "vibe-do"):
            assert re.search(rf"(?<![\w-]){re.escape(legacy_alias)}(?![\w-])", content) is None


def test_quick_start_does_not_advertise_disabled_stage_labels() -> None:
    disabled_stage_labels = (
        "Vibe: What Do I Want?",
        "Vibe: How Do We Do It?",
        "Vibe: Do It",
    )
    for path in ("docs/quick-start.en.md", "docs/quick-start.md"):
        content = _read(path)
        for label in disabled_stage_labels:
            assert label not in content


def test_install_prompts_treat_pwsh_as_default_power_shell_surface() -> None:
    prompt_paths = (
        "docs/install/prompts/full-version-install.en.md",
        "docs/install/prompts/full-version-install.md",
        "docs/install/prompts/framework-only-install.en.md",
        "docs/install/prompts/framework-only-install.md",
    )

    forbidden_phrases = (
        "must not be treated as the default prerequisite",
        "不要把 `pwsh` 当作默认前提",
    )
    for path in prompt_paths:
        content = _read(path)
        assert "pwsh" in content
        for phrase in forbidden_phrases:
            assert phrase not in content


def test_runtime_core_packaging_projections_do_not_track_local_repo_root() -> None:
    for path in (
        "config/runtime-core-packaging.full.json",
        "config/runtime-core-packaging.minimal.json",
    ):
        payload = json.loads(_read(path))
        assert "_repo_root" not in payload
