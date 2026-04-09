from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _contains_all_tokens(text: str, *tokens: str) -> bool:
    return all(token in text for token in tokens)


def test_install_prompts_define_native_mcp_first_as_completion_target() -> None:
    zh_prompt = (REPO_ROOT / "docs/install/prompts/full-version-install.md").read_text(encoding="utf-8")
    en_prompt = (REPO_ROOT / "docs/install/prompts/full-version-install.en.md").read_text(encoding="utf-8")

    assert "宿主原生 MCP" in zh_prompt
    assert "native MCP surface" in en_prompt
    assert "$vibe" in zh_prompt and "不等于 MCP" in zh_prompt
    assert "$vibe" in en_prompt and "not MCP completion" in en_prompt


def test_keyword_guard_requires_all_expected_tokens() -> None:
    assert not _contains_all_tokens("template sidecar", "template", "manifest", "sidecar")
    assert _contains_all_tokens("template manifest sidecar", "template", "manifest", "sidecar")


def test_supporting_install_docs_reject_template_and_sidecar_as_mcp_completion() -> None:
    zh_recommended = (REPO_ROOT / "docs/install/recommended-full-path.md").read_text(encoding="utf-8")
    en_recommended = (REPO_ROOT / "docs/install/recommended-full-path.en.md").read_text(encoding="utf-8")
    zh_rules = (REPO_ROOT / "docs/install/installation-rules.md").read_text(encoding="utf-8")
    en_rules = (REPO_ROOT / "docs/install/installation-rules.en.md").read_text(encoding="utf-8")

    assert _contains_all_tokens(en_recommended.lower(), "template", "manifest", "sidecar")
    assert "宿主原生 MCP" in zh_recommended
    assert "native MCP surface" in en_recommended
    assert _contains_all_tokens(zh_rules, "sidecar", "manifest")
    assert _contains_all_tokens(en_rules.lower(), "sidecar", "manifest")


def test_readme_keeps_vibe_as_runtime_entry_but_not_mcp_proof() -> None:
    readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (REPO_ROOT / "README.zh.md").read_text(encoding="utf-8")

    assert "$vibe" in readme_en
    assert "$vibe" in readme_zh
    assert "not MCP completion" in readme_en
    assert "不等于 MCP" in readme_zh
