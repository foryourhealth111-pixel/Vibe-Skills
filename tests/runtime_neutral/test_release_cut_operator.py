from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class ReleaseCutOperatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.powershell = resolve_powershell()
        if self.powershell is None:
            self.skipTest("PowerShell is required for release-cut operator tests.")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture()
        self._init_git_repo()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def _write_fixture(self) -> None:
        self._write("scripts/common/vibe-governance-helpers.ps1", (REPO_ROOT / "scripts/common/vibe-governance-helpers.ps1").read_text(encoding="utf-8"))
        self._write("scripts/governance/release-cut.ps1", (REPO_ROOT / "scripts/governance/release-cut.ps1").read_text(encoding="utf-8"))
        self._write("tools/build/sync_dist_release_manifests.py", (REPO_ROOT / "tools/build/sync_dist_release_manifests.py").read_text(encoding="utf-8"))
        self._write(
            "scripts/governance/sync-bundled-vibe.ps1",
            textwrap.dedent(
                """
                param(
                    [switch]$Preview,
                    [string]$PreviewOutputPath,
                    [switch]$PruneBundledExtras,
                    [switch]$IncludeGeneratedCompatibilityTargets
                )
                if ($Preview -and -not [string]::IsNullOrWhiteSpace($PreviewOutputPath)) {
                    $parent = Split-Path -Parent $PreviewOutputPath
                    if (-not (Test-Path -LiteralPath $parent)) {
                        New-Item -ItemType Directory -Force -Path $parent | Out-Null
                    }
                    Set-Content -LiteralPath $PreviewOutputPath -Value "{`"status`":`"preview-ok`"}" -Encoding UTF8
                }
                Write-Host "sync stub ok"
                """
            ).strip() + "\n",
        )
        governance = {
            "release": {
                "version": "9.9.8",
                "updated": "2026-03-29",
                "channel": "stable",
                "notes": "operator summary for the governed release surface",
            },
            "source_of_truth": {
                "canonical_root": ".",
                "bundled_root": "bundled/skills/vibe",
                "nested_bundled_root": "bundled/skills/vibe/bundled/skills/vibe",
            },
            "mirror_topology": {
                "canonical_target_id": "canonical",
                "sync_source_target_id": "canonical",
                "targets": [
                    {"id": "canonical", "path": ".", "role": "canonical", "required": True, "presence_policy": "required", "sync_enabled": False, "parity_policy": "authoritative"},
                    {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror", "required": False, "presence_policy": "optional", "sync_enabled": True, "parity_policy": "full"},
                    {"id": "nested_bundled", "path": "bundled/skills/vibe/bundled/skills/vibe", "role": "mirror", "required": False, "presence_policy": "optional", "sync_enabled": False, "parity_policy": "full", "materialization_mode": "release_install_only"},
                ],
            },
            "execution_context_policy": {
                "require_outer_git_root": True,
                "fail_if_script_path_is_under_mirror_root": True,
            },
            "version_markers": {
                "maintenance_files": ["SKILL.md"],
                "changelog_path": "references/changelog.md",
            },
            "logs": {
                "release_ledger_jsonl": "references/release-ledger.jsonl",
                "release_notes_dir": "docs/releases",
            },
            "packaging": {
                "mirror": {"files": [], "directories": []},
                "allow_bundled_only": [],
                "normalized_json_ignore_keys": ["updated", "generated_at"],
            },
        }

        self._write("config/version-governance.json", json.dumps(governance, ensure_ascii=False, indent=2) + "\n")
        self._write(
            "config/operator-preview-contract.json",
            json.dumps(
                {
                    "contract_version": 1,
                    "updated_at": "2026-04-04",
                    "preview_output_root": "outputs/governance/preview",
                    "machine_readable_preview_required": True,
                    "operators": {
                        "release-cut": {
                            "script": "scripts/governance/release-cut.ps1",
                            "preview_switch": "-Preview",
                            "preview_output_param": "-PreviewOutputPath",
                            "apply_gates": [
                                "scripts/verify/vibe-release-train-v2-gate.ps1",
                                "scripts/verify/vibe-release-truth-consistency-gate.ps1",
                            ],
                            "postcheck_gates": [
                                "scripts/verify/vibe-version-packaging-gate.ps1",
                                "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
                            ],
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "SKILL.md",
            textwrap.dedent(
                """
                ---
                name: vibe
                description: fixture
                ---

                ## Maintenance

                - Version: 9.9.8
                - Updated: 2026-03-29
                """
            ).strip() + "\n",
        )
        self._write("references/changelog.md", "# Changelog\n\n## v9.9.8 (2026-03-29)\n\n- Existing release.\n")
        self._write("references/release-ledger.jsonl", '{"version":"9.9.8","updated":"2026-03-29","git_head":"deadbee"}\n')
        self._write(
            "docs/releases/README.md",
            textwrap.dedent(
                """
                # Releases

                - Up: [`../README.md`](../README.md)

                ## What Lives Here

               release directory

                ## Start Here

                ### Current Release Surface

                - [`v9.9.8.md`](v9.9.8.md): old summary

                ### Release Runtime / Proof Handoff

                - runtime docs

                ## Recent Governed Releases

                - [`v9.9.8.md`](v9.9.8.md) - 2026-03-29 - old summary
                - [`v9.9.7.md`](v9.9.7.md) - 2026-03-28 - older summary

                Older release notes remain in this directory as historical version records, but they are not part of the active release surface.
                """
            ).strip() + "\n",
        )
        self._write(
            "dist/core/manifest.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "lane_id": "core",
                    "lane_kind": "universal-core",
                    "stability": "preview",
                    "source_release": {"version": "9.9.8", "updated": "2026-03-29"},
                    "summary": "core lane",
                    "runtime_ownership": {"owner": "none", "notes": "contracts only"},
                    "surface_roles": {
                        "notes": {"flat_projection_contract": True, "projection_scope": "release_lane_manifest"},
                        "runtime_authority": {"owner": "none", "notes": "contracts only"},
                        "repo_provided_entrypoints": [],
                        "proof_surfaces": [],
                        "boundary_claims": ["host_runtime"],
                    },
                    "docs": {},
                    "capability_promises": [{"id": "core"}],
                    "non_goals": ["host_runtime"],
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "dist/manifests/vibeskills-core.json",
            json.dumps(
                {
                    "manifest_kind": "vibeskills-distribution-manifest",
                    "manifest_version": 1,
                    "package_id": "vibeskills-core",
                    "status": "supported-with-constraints",
                    "runtime_role": "contract-layer",
                    "surface_roles": {
                        "notes": {"flat_projection_contract": True, "projection_scope": "public_distribution_manifest"},
                        "runtime_authority": {"runtime_role": "contract-layer", "status": "supported-with-constraints", "host_adapter_ref": None},
                        "truth_surfaces": ["docs/universalization/core-contract.md"],
                        "repo_provided_install_surfaces": [],
                        "repo_provided_payload_surfaces": [],
                        "repo_provided_reference_surfaces": [],
                        "host_managed_surfaces": [],
                        "boundary_claims": ["no runtime closure"],
                    },
                    "truth_sources": ["docs/universalization/core-contract.md"],
                    "anti_overclaim": ["no runtime closure"],
                },
                indent=2,
            )
            + "\n",
        )
        self._write("docs/universalization/core-contract.md", "# Core Contract\n")
        distribution_source = {
            "schema_version": 1,
            "release_source": {
                "governance_path": "config/version-governance.json",
                "version_pointer": "release.version",
                "updated_pointer": "release.updated",
            },
            "lane_manifests": [
                {
                    "output_path": "dist/core/manifest.json",
                    "payload": {
                        "schema_version": 1,
                        "lane_id": "core",
                        "lane_kind": "universal-core",
                        "stability": "preview",
                        "summary": "core lane",
                        "runtime_ownership": {"owner": "none", "notes": "contracts only"},
                        "docs": {},
                        "capability_promises": [{"id": "core"}],
                        "non_goals": ["host_runtime"],
                    },
                }
            ],
            "public_manifests": [
                {
                    "output_path": "dist/manifests/vibeskills-core.json",
                    "payload": {
                        "manifest_kind": "vibeskills-distribution-manifest",
                        "manifest_version": 1,
                        "package_id": "vibeskills-core",
                        "status": "supported-with-constraints",
                        "runtime_role": "contract-layer",
                        "summary": "fixture core package",
                        "truth_sources": ["docs/universalization/core-contract.md"],
                        "anti_overclaim": ["no runtime closure"],
                    },
                }
            ],
        }
        self._write("config/distribution-manifest-sources.json", json.dumps(distribution_source, ensure_ascii=False, indent=2) + "\n")

    def _init_git_repo(self) -> None:
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=self.root, capture_output=True, text=True, check=True)

    def _run_release_cut(self, *extra: str) -> subprocess.CompletedProcess[str]:
        cmd = [
            self.powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.root / "scripts" / "governance" / "release-cut.ps1"),
        ]
        cmd.extend(extra)
        return subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, check=True)

    def test_preview_lists_release_readme_and_manifest_surfaces(self) -> None:
        preview_path = self.root / "outputs" / "governance" / "preview" / "release-cut.json"
        self._run_release_cut("-Version", "9.9.9", "-Updated", "2026-03-30", "-Preview", "-PreviewOutputPath", str(preview_path), "-RunGates")
        payload = json.loads(preview_path.read_text(encoding="utf-8"))
        planned = {item["path"]: item["action"] for item in payload["preview"]["planned_file_actions"]}
        self.assertIn("docs/releases/README.md", planned)
        self.assertIn("dist/core/manifest.json", planned)
        self.assertIn("dist/manifests/vibeskills-core.json", planned)
        self.assertEqual(
            [
                "scripts/verify/vibe-release-train-v2-gate.ps1",
                "scripts/verify/vibe-release-truth-consistency-gate.ps1",
            ],
            payload["preview"]["planned_gates"],
        )
        self.assertEqual(
            [
                "scripts/verify/vibe-version-packaging-gate.ps1",
                "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
            ],
            payload["postcheck"]["verify_after_apply"],
        )


    def test_preview_postcheck_falls_back_to_apply_gates_when_contract_field_is_missing(self) -> None:
        contract_path = self.root / "config" / "operator-preview-contract.json"
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
        del payload["operators"]["release-cut"]["postcheck_gates"]
        contract_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        preview_path = self.root / "outputs" / "governance" / "preview" / "release-cut.json"
        self._run_release_cut("-Version", "9.9.9", "-Updated", "2026-03-30", "-Preview", "-PreviewOutputPath", str(preview_path), "-RunGates")
        receipt = json.loads(preview_path.read_text(encoding="utf-8"))

        self.assertEqual(receipt["preview"]["planned_gates"], receipt["postcheck"]["verify_after_apply"])

    def test_apply_updates_release_surfaces_and_creates_non_todo_note(self) -> None:
        self._run_release_cut("-Version", "9.9.9", "-Updated", "2026-03-30")

        readme = (self.root / "docs" / "releases" / "README.md").read_text(encoding="utf-8")
        self.assertIn("- [`v9.9.9.md`](v9.9.9.md): operator summary for the governed release surface", readme)
        recent_lines = [line for line in readme.splitlines() if line.startswith("- [`v9.")]
        self.assertEqual("- [`v9.9.9.md`](v9.9.9.md) - 2026-03-30 - operator summary for the governed release surface", recent_lines[1 if "Current Release Surface" in readme else 0])

        core_manifest = json.loads((self.root / "dist" / "core" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("9.9.9", core_manifest["source_release"]["version"])
        self.assertEqual("2026-03-30", core_manifest["source_release"]["updated"])
        self.assertEqual("none", core_manifest["surface_roles"]["runtime_authority"]["owner"])
        self.assertEqual(["host_runtime"], core_manifest["surface_roles"]["boundary_claims"])

        public_manifest = json.loads((self.root / "dist" / "manifests" / "vibeskills-core.json").read_text(encoding="utf-8"))
        self.assertEqual("9.9.9", public_manifest["source_release"]["version"])
        self.assertEqual("2026-03-30", public_manifest["source_release"]["updated"])
        self.assertEqual("contract-layer", public_manifest["surface_roles"]["runtime_authority"]["runtime_role"])
        self.assertEqual(["no runtime closure"], public_manifest["surface_roles"]["boundary_claims"])

        note = (self.root / "docs" / "releases" / "v9.9.9.md").read_text(encoding="utf-8")
        self.assertIn("## Validation Notes", note)
        self.assertIn("## Migration Notes", note)
        self.assertNotIn("TODO", note.upper())


if __name__ == "__main__":
    unittest.main()
