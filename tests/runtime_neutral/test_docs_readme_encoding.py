from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_README = REPO_ROOT / "docs" / "README.md"


class DocsReadmeNavigationTests(unittest.TestCase):
    def assertReadableEntry(self, text: str, link_prefix: str, readable_snippet: str) -> None:
        self.assertIn(link_prefix, text)
        self.assertIn(readable_snippet, text)

    def test_docs_landing_page_has_readable_install_navigation(self) -> None:
        text = DOCS_README.read_text(encoding="utf-8")

        self.assertReadableEntry(
            text,
            "- [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)：",
            "唯一公开安装入口",
        )
        self.assertReadableEntry(
            text,
            "- [`install/README.md`](./install/README.md)：",
            "安装索引",
        )
        self.assertReadableEntry(
            text,
            "- [`cold-start-install-paths.md`](./cold-start-install-paths.md)：",
            "冷启动路径",
        )

        self.assertNotIn(
            "锛氶潰鍚戞櫘閫氱敤鎴风殑涓€閿畨瑁呭彂甯冩枃妗堜笌 AI 鍔╂墜澶嶅埗鎻愮ず璇?",
            text,
        )
        self.assertNotIn(
            "锛歡rdinary-user public release copy and copy-paste onboarding prompt",
            text,
        )


if __name__ == "__main__":
    unittest.main()
