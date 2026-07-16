from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATHS = (
    ROOT / "SKILL.md",
    ROOT / "core" / "skills" / "vibe" / "instruction.md",
)


def test_canonical_prompt_preserves_the_current_user_task_without_chat_history() -> None:
    required_contract = (
        "current user task",
        "verbatim",
        "unrelated chat history",
        "Do not summarize, rewrite, or reduce it to keywords",
        "exact input paths",
        "input immutability constraints",
        "exact output roots",
        "synthetic-data evidence boundaries",
        "module dependencies and safe parallel boundaries",
        "acceptance criteria",
    )
    forbidden_contract = (
        "Extract core intent as keyword text",
        "<extracted keyword intent text>",
    )

    for path in CONTRACT_PATHS:
        text = path.read_text(encoding="utf-8")
        for phrase in required_contract:
            assert phrase in text, f"{path.name} must require {phrase!r}"
        for phrase in forbidden_contract:
            assert phrase not in text, f"{path.name} still permits lossy task compression"


def test_every_canonical_entry_prompt_uses_the_lossless_task_specification() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert text.count("--prompt \"<current user task, verbatim>\"") == 3
    assert "<stable continuation intent" not in text
