from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DISCLOSURE_POLICY = json.loads((REPO_ROOT / "config" / "memory-disclosure-policy.json").read_text(encoding="utf-8"))


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


def run_governed_runtime(task: str, artifact_root: Path, env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-memory-disclosure-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    effective_env["VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION"] = "1"

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=effective_env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


class MemoryProgressiveDisclosureTests(unittest.TestCase):
    def test_related_runs_emit_disclosure_levels_and_capsule_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            env = {
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "backends"),
                "SERENA_PROJECT_KEY": "pytest-memory-disclosure-project",
            }

            run_governed_runtime(
                "XL approved decision: keep api worker runtime continuity and graph relationship between api worker and planner.",
                artifact_root=temp_root / "seed-run",
                env=env,
            )
            second = run_governed_runtime(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root / "follow-up-run",
                env=env,
            )

            report = json.loads(
                Path(second["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )
            stage_by_name = {stage["stage"]: stage for stage in report["stages"]}

            requirement_context = stage_by_name["requirement_doc"]["context_injection"]
            plan_context = stage_by_name["xl_plan"]["context_injection"]
            execute_context = stage_by_name["plan_execute"]["context_injection"]

            self.assertEqual(
                DISCLOSURE_POLICY["stages"]["requirement_doc"]["level"],
                requirement_context["disclosure_level"],
            )
            self.assertEqual(
                DISCLOSURE_POLICY["stages"]["xl_plan"]["level"],
                plan_context["disclosure_level"],
            )
            self.assertEqual(
                DISCLOSURE_POLICY["stages"]["plan_execute"]["level"],
                execute_context["disclosure_level"],
            )

            for stage_name, context in (
                ("requirement_doc", requirement_context),
                ("xl_plan", plan_context),
                ("plan_execute", execute_context),
            ):
                with self.subTest(context=context["disclosure_level"]):
                    self.assertLessEqual(
                        context["capsule_count"],
                        DISCLOSURE_POLICY["stages"][stage_name]["max_capsules"],
                    )
                    self.assertGreaterEqual(context["capsule_count"], 1)
                    self.assertTrue(Path(context["artifact_path"]).exists())
                    self.assertGreaterEqual(len(context["selected_capsules"]), 1)
                    first = context["selected_capsules"][0]
                    self.assertIn("capsule_id", first)
                    self.assertIn("owner", first)
                    self.assertIn("lane", first)
                    self.assertIn("kind", first)
                    self.assertIn("title", first)
                    self.assertIn("why_now", first)
                    self.assertIn("expansion_ref", first)
                    self.assertIn("updated_at", first)

                    match = re.match(r"^(?P<artifact>.+)#(?P<capsule>[^#]+)$", str(first["expansion_ref"]))
                    self.assertIsNotNone(match)
                    artifact_path = Path(match.group("artifact"))
                    self.assertTrue(artifact_path.exists())

                    backend_response = json.loads(artifact_path.read_text(encoding="utf-8"))
                    matching_capsule = next(
                        capsule
                        for capsule in backend_response["capsules"]
                        if capsule["capsule_id"] == match.group("capsule")
                    )
                    self.assertEqual(first["capsule_id"], matching_capsule["capsule_id"])
                    self.assertEqual(first["owner"], matching_capsule["owner"])
                    self.assertEqual(first["lane"], matching_capsule["lane"])
                    self.assertEqual(first["kind"], matching_capsule["kind"])
                    self.assertEqual(first["updated_at"], matching_capsule["updated_at"])

    def test_requirement_and_plan_docs_render_capsule_expansion_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            env = {
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "backends"),
                "SERENA_PROJECT_KEY": "pytest-memory-disclosure-docs",
            }

            run_governed_runtime(
                "Approved decision: reuse bounded memory capsules for release planning and execution evidence.",
                artifact_root=temp_root / "seed-run",
                env=env,
            )
            second = run_governed_runtime(
                "Plan the next release using bounded memory capsules and prior execution evidence.",
                artifact_root=temp_root / "follow-up-run",
                env=env,
            )

            requirement_text = Path(second["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            plan_text = Path(second["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8")

            self.assertIn("## Memory Context", requirement_text)
            self.assertIn("Capsule", requirement_text)
            self.assertIn("Expansion Ref", requirement_text)
            self.assertIn("## Memory Context", plan_text)
            self.assertIn("Capsule", plan_text)
            self.assertIn("Expansion Ref", plan_text)


if __name__ == "__main__":
    unittest.main()
