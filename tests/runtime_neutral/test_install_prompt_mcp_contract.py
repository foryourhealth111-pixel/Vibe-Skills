from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILES = [
    REPO_ROOT / "docs" / "install" / "prompts" / "full-version-install.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "full-version-install.en.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "framework-only-install.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "framework-only-install.en.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "full-version-update.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "full-version-update.en.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "framework-only-update.md",
    REPO_ROOT / "docs" / "install" / "prompts" / "framework-only-update.en.md",
]
SUPPORTING_DOCS = [
    REPO_ROOT / "docs" / "install" / "recommended-full-path.md",
    REPO_ROOT / "docs" / "install" / "recommended-full-path.en.md",
    REPO_ROOT / "docs" / "one-shot-setup.md",
]
PUBLIC_INSTALL_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "README.zh.md",
    REPO_ROOT / "docs" / "quick-start.md",
    REPO_ROOT / "docs" / "quick-start.en.md",
    REPO_ROOT / "docs" / "install" / "README.md",
    REPO_ROOT / "docs" / "install" / "README.en.md",
    REPO_ROOT / "docs" / "install" / "one-click-install-release-copy.md",
    REPO_ROOT / "docs" / "install" / "one-click-install-release-copy.en.md",
    REPO_ROOT / "docs" / "install" / "recommended-full-path.md",
    REPO_ROOT / "docs" / "install" / "recommended-full-path.en.md",
    REPO_ROOT / "docs" / "install" / "manual-copy-install.md",
    REPO_ROOT / "docs" / "install" / "manual-copy-install.en.md",
    REPO_ROOT / "docs" / "install" / "configuration-guide.md",
    REPO_ROOT / "docs" / "install" / "configuration-guide.en.md",
    REPO_ROOT / "docs" / "one-shot-setup.md",
    *PROMPT_FILES,
]
INSTALL_USER_VISIBLE_SURFACES = [
    REPO_ROOT / "config" / "settings.template.codex.json",
    REPO_ROOT / "config" / "settings.template.claude.json",
    REPO_ROOT / "scripts" / "bootstrap" / "one-shot-setup.ps1",
    REPO_ROOT / "scripts" / "bootstrap" / "one-shot-setup.sh",
    REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "bootstrap_doctor.py",
    REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "bootstrap_doctor_runtime.py",
    REPO_ROOT / "scripts" / "verify" / "vibe-bootstrap-doctor-gate.ps1",
]
HIDDEN_ONLINE_CONFIG_TOKENS = (
    "VCO_INTENT_ADVICE",
    "VCO_VECTOR_DIFF",
    "OPENAI_*",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)


def _has_vibe_mcp_disclaimer(text: str, lowered: str) -> bool:
    return (
        ("$vibe" not in text and "/vibe" not in text)
        or "not mcp completion" in lowered
        or "not proof of mcp" in lowered
        or "不等于mcp" in text
        or "不等于 MCP" in text
    )


class InstallPromptMcpContractTests(unittest.TestCase):
    def test_supporting_doc_vibe_guard_handles_slash_vibe_and_not_proof_variant(self) -> None:
        self.assertFalse(_has_vibe_mcp_disclaimer("/vibe is available", "/vibe is available"))
        self.assertTrue(
            _has_vibe_mcp_disclaimer(
                "/vibe is available and not proof of mcp",
                "/vibe is available and not proof of mcp",
            )
        )

    def test_all_prompt_docs_require_the_same_five_mcp_surfaces(self) -> None:
        for path in PROMPT_FILES:
            text = path.read_text(encoding="utf-8-sig")
            lowered = text.lower()
            for server_name in ("github", "context7", "serena", "scrapling", "claude-flow"):
                self.assertIn(server_name, text, path.name)
            self.assertTrue(
                "final install report" in lowered or "最终安装汇报" in text or "最终安装报告" in text,
                path.name,
            )
            self.assertTrue(
                "installed locally" in lowered or "本地安装完成" in text,
                path.name,
            )
            self.assertTrue(
                "native mcp surface" in lowered or "宿主原生mcp" in lowered or "宿主原生 mcp" in lowered,
                path.name,
            )
            self.assertTrue("$vibe" in text or "/vibe" in text, path.name)
            self.assertTrue(
                "not mcp completion" in lowered
                or "not proof of mcp" in lowered
                or "不等于mcp" in text
                or "不等于 MCP" in text,
                path.name,
            )
            self.assertIn("online-ready", lowered, path.name)

    def test_supporting_install_docs_describe_non_blocking_mcp_attempts(self) -> None:
        for path in SUPPORTING_DOCS:
            text = path.read_text(encoding="utf-8-sig")
            lowered = text.lower()
            self.assertIn("scrapling", text, path.name)
            self.assertIn("claude-flow", text, path.name)
            self.assertTrue("manual follow-up" in lowered or "手动处理" in text, path.name)
            self.assertTrue(
                "native mcp surface" in lowered or "宿主原生mcp" in lowered or "宿主原生 mcp" in lowered,
                path.name,
            )
            self.assertTrue(
                _has_vibe_mcp_disclaimer(text, lowered),
                path.name,
            )
            self.assertIn("online-ready", lowered, path.name)

    def test_public_install_docs_do_not_expose_hidden_online_config_keys(self) -> None:
        for path in PUBLIC_INSTALL_DOCS:
            text = path.read_text(encoding="utf-8-sig")
            for token in HIDDEN_ONLINE_CONFIG_TOKENS:
                self.assertNotIn(token, text, path.name)

    def test_install_user_visible_surfaces_do_not_expose_hidden_online_config_keys(self) -> None:
        for path in INSTALL_USER_VISIBLE_SURFACES:
            text = path.read_text(encoding="utf-8-sig")
            for token in HIDDEN_ONLINE_CONFIG_TOKENS:
                self.assertNotIn(token, text, path.name)


if __name__ == "__main__":
    unittest.main()
