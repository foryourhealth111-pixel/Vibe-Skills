from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"


def run_package_install(*, host: str, target_root: Path, profile: str = "full") -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(CONTRACTS_SRC), str(INSTALLER_CORE_SRC), env.get("PYTHONPATH", "")]).strip(os.pathsep)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vgo_installer.install_runtime",
            "--repo-root",
            str(REPO_ROOT),
            "--target-root",
            str(target_root),
            "--host",
            host,
            "--profile",
            profile,
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result, json.loads(result.stdout)


class GlobalInstructionBootstrapRuntimeTests(unittest.TestCase):
    def test_codex_install_materializes_single_global_bootstrap_block(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)

            _, payload = run_package_install(host="codex", target_root=target_root)

            bootstrap_path = target_root / "AGENTS.md"
            receipt_path = Path(str(payload["global_instruction_bootstrap_receipt"]))
            self.assertTrue(bootstrap_path.exists())
            self.assertTrue(receipt_path.exists())
            self.assertEqual("codex", payload["host_id"])
            bootstrap_text = bootstrap_path.read_text(encoding="utf-8")
            self.assertEqual(1, bootstrap_text.count("<!-- VIBESKILLS:BEGIN managed-block"))
            self.assertIn("Do not silently continue in ordinary mode first.", bootstrap_text)
            self.assertIn("Reading this bootstrap block alone is not proof of canonical vibe entry.", bootstrap_text)
            self.assertIn("Do not preflight-scan the current workspace or repository for canonical proof files before launch.", bootstrap_text)
            self.assertIn("only after canonical-entry returns a session root may you validate proof artifacts inside that session root.", bootstrap_text)
            self.assertIn("host-launch-receipt.json", bootstrap_text)

            wrapper_text = (target_root / "commands" / "vibe-how.md").read_text(encoding="utf-8")
            self.assertIn('"schema": "vibe-wrapper-trampoline/v1"', wrapper_text)
            self.assertIn('"launch_mode": "canonical-entry"', wrapper_text)
            self.assertIn('"host_id": "codex"', wrapper_text)
            self.assertIn('"entry_id": "vibe-how"', wrapper_text)
            self.assertNotIn("Use the `vibe` skill", wrapper_text)

    def test_reinstall_keeps_single_block_and_reports_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)

            run_package_install(host="codex", target_root=target_root)
            _, payload = run_package_install(host="codex", target_root=target_root)

            receipt_path = Path(str(payload["global_instruction_bootstrap_receipt"]))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            bootstrap_text = (target_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual("unchanged", receipt["action"])
            self.assertEqual(1, bootstrap_text.count("<!-- VIBESKILLS:BEGIN managed-block"))
            self.assertEqual(str(receipt_path), payload["global_instruction_bootstrap_receipt"])

    def test_claude_install_preserves_existing_claude_md_content(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            bootstrap_path = target_root / "CLAUDE.md"
            bootstrap_path.write_text("# Personal CLAUDE rules\n\n- Keep this line.\n", encoding="utf-8")

            run_package_install(host="claude-code", target_root=target_root)

            merged = bootstrap_path.read_text(encoding="utf-8")
            self.assertIn("# Personal CLAUDE rules", merged)
            self.assertIn("Keep this line.", merged)
            self.assertEqual(1, merged.count("<!-- VIBESKILLS:BEGIN managed-block"))
            self.assertIn("Reading this bootstrap block alone is not proof of canonical vibe entry.", merged)
            self.assertIn("Do not preflight-scan the current workspace or repository for canonical proof files before launch.", merged)
            self.assertIn("only after canonical-entry returns a session root may you validate proof artifacts inside that session root.", merged)
            self.assertIn("host-launch-receipt.json", merged)
            wrapper_text = (target_root / "skills" / "vibe-how" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn('"schema": "vibe-wrapper-trampoline/v1"', wrapper_text)
            self.assertIn('"launch_mode": "canonical-entry"', wrapper_text)
            self.assertIn('"host_id": "claude-code"', wrapper_text)
            self.assertIn('"entry_id": "vibe-how"', wrapper_text)
            self.assertNotIn("Use the `vibe` skill", wrapper_text)

    def test_opencode_install_preserves_existing_agents_md_and_real_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            agents_path = target_root / "AGENTS.md"
            agents_path.write_text("# Existing OpenCode rules\n", encoding="utf-8")
            real_config = target_root / "opencode.json"
            original = {"$schema": "https://opencode.ai/config.json", "mcp": {"playwright": {"enabled": True}}}
            real_config.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

            run_package_install(host="opencode", target_root=target_root)

            merged = agents_path.read_text(encoding="utf-8")
            self.assertIn("# Existing OpenCode rules", merged)
            self.assertEqual(1, merged.count("<!-- VIBESKILLS:BEGIN managed-block"))
            self.assertIn("Do not silently continue in ordinary mode first.", merged)
            self.assertIn("Reading this bootstrap block alone is not proof of canonical vibe entry.", merged)
            self.assertIn("Do not preflight-scan the current workspace or repository for canonical proof files before launch.", merged)
            self.assertIn("only after canonical-entry returns a session root may you validate proof artifacts inside that session root.", merged)
            self.assertIn("host-launch-receipt.json", merged)
            self.assertEqual(original, json.loads(real_config.read_text(encoding="utf-8")))
            wrapper_text = (target_root / "commands" / "vibe-how.md").read_text(encoding="utf-8")
            self.assertIn('"schema": "vibe-wrapper-trampoline/v1"', wrapper_text)
            self.assertIn('"launch_mode": "canonical-entry"', wrapper_text)
            self.assertIn('"host_id": "opencode"', wrapper_text)
            self.assertIn('"entry_id": "vibe-how"', wrapper_text)
            self.assertIn("agent: vibe-plan", wrapper_text)
            self.assertNotIn("Use the `vibe` skill", wrapper_text)

    def test_bootstrap_receipts_are_scoped_per_host_surface_with_shared_target_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)

            _, codex_payload = run_package_install(host="codex", target_root=target_root)
            _, opencode_payload = run_package_install(host="opencode", target_root=target_root)

            codex_receipt = Path(str(codex_payload["global_instruction_bootstrap_receipt"]))
            opencode_receipt = Path(str(opencode_payload["global_instruction_bootstrap_receipt"]))

            self.assertTrue(codex_receipt.exists())
            self.assertTrue(opencode_receipt.exists())
            self.assertNotEqual(codex_receipt, opencode_receipt)
            self.assertEqual("codex", json.loads(codex_receipt.read_text(encoding="utf-8"))["host"])
            self.assertEqual("opencode", json.loads(opencode_receipt.read_text(encoding="utf-8"))["host"])

    def test_shared_target_root_keeps_independent_codex_and_opencode_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)

            run_package_install(host="codex", target_root=target_root)
            run_package_install(host="opencode", target_root=target_root)

            merged = (target_root / "AGENTS.md").read_text(encoding="utf-8")

            self.assertEqual(2, merged.count("<!-- VIBESKILLS:BEGIN managed-block"))
            self.assertIn("host=codex block=global-vibe-bootstrap", merged)
            self.assertIn("host=opencode block=global-vibe-bootstrap", merged)
