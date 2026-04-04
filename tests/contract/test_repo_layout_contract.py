from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_clean_architecture_roots_exist() -> None:
    for rel in ["packages", "apps", "platform", "tools", "docs/architecture"]:
        assert (ROOT / rel).exists(), rel
