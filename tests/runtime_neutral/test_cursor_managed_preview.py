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


class CursorManagedPreviewTests(unittest.TestCase):
    def test_python_installer_materializes_cursor_host_closure_and_sidecar_only_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            _, payload = run_package_install(host="cursor", target_root=target_root)
            closure_path = target_root / ".vibeskills" / "host-closure.json"
            host_settings_path = target_root / ".vibeskills" / "host-settings.json"

            self.assertEqual("cursor", payload["host_id"])
            self.assertEqual("preview-guidance", payload["install_mode"])
            self.assertTrue(closure_path.exists())
            self.assertTrue(host_settings_path.exists())
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertFalse((target_root / "settings.json").exists())
            self.assertFalse((target_root / "commands").exists())

            closure = json.loads(closure_path.read_text(encoding="utf-8"))
            host_settings = json.loads(host_settings_path.read_text(encoding="utf-8"))

            self.assertEqual("cursor", closure["host_id"])
            self.assertEqual(str(target_root.resolve()), closure["target_root"])
            self.assertEqual(str(target_root.resolve()), closure["runtime_root"])
            self.assertEqual(str(target_root.resolve()), closure["host_bridge_root"])
            self.assertEqual(payload["desired_shared_runtime_root"], closure["desired_shared_runtime_root"])
            self.assertEqual("legacy-host-root-override", closure["runtime_layout_mode"])
            self.assertEqual("cursor", host_settings["host_id"])
            self.assertEqual(str(target_root.resolve()), host_settings["runtime_root"])
            self.assertEqual(str(target_root.resolve()), host_settings["host_bridge_root"])
            self.assertEqual(payload["desired_shared_runtime_root"], host_settings["desired_shared_runtime_root"])
            self.assertEqual("legacy-host-root-override", host_settings["runtime_layout_mode"])
            self.assertEqual(str((target_root / "skills").resolve()), host_settings["skills_root"])
            self.assertEqual(str(target_root.resolve()), payload["runtime_root"])
            self.assertEqual(str(target_root.resolve()), payload["host_bridge_root"])
            self.assertNotEqual(str(target_root.resolve()), payload["desired_shared_runtime_root"])
            self.assertEqual("legacy-host-root-override", payload["runtime_layout_mode"])
            self.assertEqual(
                [str((target_root / "skills" / "vibe" / "SKILL.md").resolve())],
                payload["host_visible_entry_paths"],
            )
            retired_fields = {
                "specialist_execution",
                "specialist_wrapper",
                "specialist_wrapper_ready",
                "same_session_specialist_routing",
            }
            self.assertTrue(retired_fields.isdisjoint(payload))
            self.assertTrue(retired_fields.isdisjoint(closure))
            self.assertTrue(retired_fields.isdisjoint(host_settings))


if __name__ == "__main__":
    unittest.main()
