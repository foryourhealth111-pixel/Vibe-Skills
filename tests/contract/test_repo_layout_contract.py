from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT_ARCHITECTURE_ROOTS = [
    "packages",
    "apps",
    "adapters",
    "scripts",
    "protocols",
    "docs/architecture",
]
RETIRED_ARCHITECTURE_ROOTS = [
    "platform",
    "tools",
]
REQUIRED_CODEX_VIBE_WRAPPER_SKILLS = [
    "bundled/skills/vibe-what-do-i-want/SKILL.md",
    "bundled/skills/vibe-how-do-we-do/SKILL.md",
    "bundled/skills/vibe-do-it/SKILL.md",
    "bundled/skills/vibe-upgrade/SKILL.md",
]


def test_clean_architecture_roots_exist() -> None:
    for rel in CURRENT_ARCHITECTURE_ROOTS:
        assert (ROOT / rel).exists(), rel


def test_retired_top_level_roots_do_not_reappear() -> None:
    for rel in RETIRED_ARCHITECTURE_ROOTS:
        assert not (ROOT / rel).exists(), rel


def test_codex_vibe_wrapper_skill_sources_exist() -> None:
    for rel in REQUIRED_CODEX_VIBE_WRAPPER_SKILLS:
        assert (ROOT / rel).exists(), rel
