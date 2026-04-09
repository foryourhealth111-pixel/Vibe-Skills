from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_REGISTRY_MODULE = REPO_ROOT / "packages" / "installer-core" / "src" / "vgo_installer" / "adapter_registry.py"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


class OpenClawRuntimeCoreTests(unittest.TestCase):
    EXPECTED_WRAPPER_SKILLS = ("vibe", "vibe-want", "vibe-how", "vibe-do")

    def test_adapter_registry_exposes_openclaw_preview_runtime_core_lane(self) -> None:
        registry = _load_module("installer_adapter_registry_openclaw", ADAPTER_REGISTRY_MODULE)
        payload = registry.resolve_adapter(REPO_ROOT, "openclaw")
        self.assertEqual("openclaw", payload["id"])
        self.assertEqual("preview", payload["status"])
        self.assertEqual("runtime-core", payload["install_mode"])
        self.assertEqual(".openclaw", payload["default_target_root"]["rel"])
        self.assertEqual("host-home", payload["default_target_root"]["kind"])
        self.assertEqual("runtime-core-preview", payload["closure_json"]["closure_level"])
        self.assertEqual("preview", payload["host_profile_json"]["status"])
        self.assertEqual("~/.openclaw", payload["host_profile_json"]["settings_surface"]["path"])
        self.assertIn(
            "global_workflows/** when commands exist",
            payload["closure_json"]["host_state_written"],
        )
        self.assertIn(
            "mcp_config.json when absent",
            payload["closure_json"]["host_state_written"],
        )

    def test_python_installer_uses_runtime_core_with_preview_lane_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            _, payload = run_package_install(host="openclaw", target_root=target_root)

            self.assertEqual("openclaw", payload["host_id"])
            self.assertEqual("runtime-core", payload["install_mode"])
            self.assertIn("host_closure_path", payload)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "skills" / "vibe" / "bundled" / "skills" / "brainstorming" / "SKILL.runtime-mirror.md").exists())
            for name in self.EXPECTED_WRAPPER_SKILLS:
                self.assertTrue((target_root / "skills" / name / "SKILL.md").exists())
            self.assertFalse((target_root / "skills" / "brainstorming").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-closure.json").exists())
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "global_workflows").exists())
            self.assertFalse((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())
            self.assertFalse((target_root / "config" / "plugins-manifest.codex.json").exists())

    def test_shell_install_and_check_support_openclaw_runtime_core_preview_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "openclaw",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host   : openclaw", install_result.stdout)
            self.assertIn("Mode   : runtime-core", install_result.stdout)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            for name in self.EXPECTED_WRAPPER_SKILLS:
                self.assertTrue((target_root / "skills" / name / "SKILL.md").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-closure.json").exists())
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "global_workflows").exists())
            self.assertFalse((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())

            check_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "openclaw",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host: openclaw", check_result.stdout)
            self.assertIn("Mode: runtime-core", check_result.stdout)
            self.assertIn("[OK] host closure manifest", check_result.stdout)
            self.assertIn("[OK] host-visible discoverable entries", check_result.stdout)
            self.assertIn("[OK] npm check skipped for non-governed adapter mode", check_result.stdout)
            self.assertNotIn("[FAIL] settings.json", check_result.stdout)
            self.assertNotIn("[FAIL] config/plugins-manifest.codex.json", check_result.stdout)
            self.assertNotIn("[FAIL] mcp_config.json", check_result.stdout)


if __name__ == "__main__":
    unittest.main()
