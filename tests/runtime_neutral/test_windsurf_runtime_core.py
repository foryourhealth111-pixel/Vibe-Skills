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


class WindsurfRuntimeCoreTests(unittest.TestCase):
    def test_adapter_registry_exposes_windsurf_parallel_root(self) -> None:
        registry = _load_module("installer_adapter_registry_windsurf", ADAPTER_REGISTRY_MODULE)
        payload = registry.resolve_adapter(REPO_ROOT, "windsurf")
        self.assertEqual("windsurf", payload["id"])
        self.assertEqual("runtime-core", payload["install_mode"])
        self.assertEqual(".codeium/windsurf", payload["default_target_root"]["rel"])

    def test_python_installer_uses_runtime_core_without_codex_host_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            _, payload = run_package_install(host="windsurf", target_root=target_root)

            self.assertEqual("windsurf", payload["host_id"])
            self.assertEqual("runtime-core", payload["install_mode"])
            self.assertIn("host_closure_path", payload)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "skills" / "brainstorming" / "SKILL.md").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-closure.json").exists())
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "global_workflows").exists())
            self.assertFalse((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())
            self.assertFalse((target_root / "config" / "plugins-manifest.codex.json").exists())

    def test_shell_install_and_check_support_windsurf_runtime_core(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "windsurf",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host   : windsurf", install_result.stdout)
            self.assertIn("Mode   : runtime-core", install_result.stdout)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
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
                    "windsurf",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host: windsurf", check_result.stdout)
            self.assertIn("[OK] host closure manifest", check_result.stdout)
            self.assertNotIn("[FAIL] settings.json", check_result.stdout)
            self.assertNotIn("[FAIL] mcp_config.json", check_result.stdout)


if __name__ == "__main__":
    unittest.main()
