from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
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


def run_governed_runtime(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-memory-runtime-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode benchmark_autonomous "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


class MemoryRuntimeActivationTests(unittest.TestCase):
    def test_runtime_emits_stage_aware_memory_activation_report(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_governed_runtime(
                "Plan and debug a governed runtime enhancement with long-horizon continuity needs.",
                artifact_root=Path(tempdir),
            )
            summary = payload["summary"]
            artifacts = summary["artifacts"]

            self.assertIn("memory_activation_report", artifacts)
            self.assertIn("memory_activation_markdown", artifacts)

            report_path = Path(artifacts["memory_activation_report"])
            markdown_path = Path(artifacts["memory_activation_markdown"])

            self.assertTrue(report_path.exists())
            self.assertTrue(markdown_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], report["run_id"])
            self.assertEqual("shadow", report["policy"]["mode"])
            self.assertEqual("advisory_first_post_route_only", report["policy"]["routing_contract"])
            self.assertEqual("state_store", report["policy"]["canonical_owners"]["session"])
            self.assertEqual("Serena", report["policy"]["canonical_owners"]["project_decision"])
            self.assertEqual("ruflo", report["policy"]["canonical_owners"]["short_term_semantic"])
            self.assertEqual("Cognee", report["policy"]["canonical_owners"]["long_term_graph"])

            stages = report["stages"]
            self.assertEqual(
                [
                    "skeleton_check",
                    "deep_interview",
                    "requirement_doc",
                    "xl_plan",
                    "plan_execute",
                    "phase_cleanup",
                ],
                [stage["stage"] for stage in stages],
            )

            skeleton = stages[0]
            self.assertEqual("fallback_local_digest", skeleton["read_actions"][0]["status"])
            self.assertLessEqual(
                len(skeleton["read_actions"][0]["items"]),
                skeleton["read_actions"][0]["budget"]["top_k"],
            )

            deep_interview = stages[1]
            self.assertEqual("deferred_no_project_key", deep_interview["read_actions"][0]["status"])

            requirement_stage = stages[2]
            self.assertGreaterEqual(requirement_stage["context_injection"]["injected_item_count"], 1)
            self.assertLessEqual(
                requirement_stage["context_injection"]["estimated_tokens"],
                requirement_stage["context_injection"]["budget"]["max_tokens"],
            )

            execute_stage = stages[4]
            self.assertGreaterEqual(execute_stage["write_actions"][0]["item_count"], 1)
            self.assertTrue(Path(execute_stage["write_actions"][0]["artifact_path"]).exists())
            self.assertIn(
                execute_stage["write_actions"][0]["status"],
                {"fallback_local_artifact", "backend_write"},
            )

            cleanup_stage = stages[5]
            self.assertEqual("guarded_no_write", cleanup_stage["write_actions"][0]["status"])
            self.assertTrue(Path(cleanup_stage["write_actions"][1]["artifact_path"]).exists())
            self.assertEqual("generated_local_fold", cleanup_stage["write_actions"][1]["status"])

            summary_block = report["summary"]
            self.assertEqual(6, summary_block["stage_count"])
            self.assertGreaterEqual(summary_block["fallback_event_count"], 1)
            self.assertGreaterEqual(summary_block["artifact_count"], 3)
            self.assertTrue(summary_block["budget_guard_respected"])


if __name__ == "__main__":
    unittest.main()
