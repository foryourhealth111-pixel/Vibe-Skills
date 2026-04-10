from __future__ import annotations

import json
import os
import shutil
import stat
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


def create_fake_codex_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex{suffix}"
    if os.name == "nt":
        command_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
            "set OUT=\r\n"
            ":loop\r\n"
            "if \"%~1\"==\"\" goto done\r\n"
            "if /I \"%~1\"==\"-o\" (\r\n"
            "  set OUT=%~2\r\n"
            "  shift\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "shift\r\n"
            "goto loop\r\n"
            ":done\r\n"
            "if \"%OUT%\"==\"\" exit /b 2\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}\r\n"
            "echo fake codex ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        command_path.write_text(
            "#!/usr/bin/env sh\n"
            "OUT=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -o)\n"
            "      OUT=\"$2\"\n"
            "      shift 2\n"
            "      ;;\n"
            "    *)\n"
            "      shift\n"
            "      ;;\n"
            "  esac\n"
            "done\n"
            "if [ -z \"$OUT\" ]; then\n"
            "  exit 2\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}' > \"$OUT\"\n"
            "printf 'fake codex ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def run_governed_runtime(task: str, artifact_root: Path, env: dict[str, str] | None = None) -> dict[str, object]:
    payload, _ = run_governed_runtime_with_metadata(task, artifact_root, env=env)
    return payload


def run_governed_runtime_with_metadata(
    task: str,
    artifact_root: Path,
    env: dict[str, str] | None = None,
    *,
    check: bool = True,
) -> tuple[dict[str, object], str]:
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
        check=check,
    )
    if not check and completed.returncode != 0:
        return (
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            run_id,
        )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout), run_id


class MemoryRuntimeActivationTests(unittest.TestCase):
    def test_runtime_activation_report_keeps_required_stage_shape_and_owner_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_governed_runtime(
                "Audit current governed memory activation contracts before refactoring shared memory.",
                artifact_root=Path(tempdir),
            )
            report = json.loads(
                Path(payload["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )

            stages = report["stages"]
            self.assertEqual(6, len(stages))

            stage_by_name = {stage["stage"]: stage for stage in stages}
            self.assertEqual(
                {"state_store", "Cognee"},
                {action["owner"] for action in stage_by_name["skeleton_check"]["read_actions"]},
            )
            self.assertEqual(
                {"Serena", "Cognee"},
                {action["owner"] for action in stage_by_name["xl_plan"]["read_actions"]},
            )
            self.assertEqual(
                {"state_store", "ruflo"},
                {action["owner"] for action in stage_by_name["plan_execute"]["write_actions"]},
            )
            self.assertEqual(
                {"Serena", "state_store", "Cognee"},
                {action["owner"] for action in stage_by_name["phase_cleanup"]["write_actions"]},
            )

            for stage in stages:
                with self.subTest(stage=stage["stage"]):
                    self.assertIn("read_actions", stage)
                    self.assertIn("write_actions", stage)
                    self.assertIn("context_injection", stage)
                    if stage["stage"] in {"requirement_doc", "xl_plan", "plan_execute"}:
                        self.assertIsInstance(stage["context_injection"], dict)
                        self.assertIn("injected_item_count", stage["context_injection"])
                        self.assertIn("estimated_tokens", stage["context_injection"])
                        self.assertIn("disclosure_level", stage["context_injection"])
                        self.assertIn("selected_capsules", stage["context_injection"])
                    else:
                        self.assertIsNone(stage["context_injection"])

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

    def test_runtime_reads_and_writes_real_memory_backends_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            backend_root = temp_root / "backends"
            env = os.environ.copy()
            env["VIBE_MEMORY_BACKEND_ROOT"] = str(backend_root)
            env["SERENA_PROJECT_KEY"] = "pytest-memory-project"

            first = run_governed_runtime(
                "XL approved decision: keep api worker runtime continuity and graph relationship between api worker and planner.",
                artifact_root=temp_root / "run-1",
                env=env,
            )
            first_report = json.loads(
                Path(first["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )
            first_execute = first_report["stages"][4]
            first_cleanup = first_report["stages"][5]

            self.assertEqual("backend_write", first_execute["write_actions"][1]["status"])
            self.assertEqual("backend_write", first_cleanup["write_actions"][0]["status"])
            self.assertEqual("backend_write", first_cleanup["write_actions"][2]["status"])

            second = run_governed_runtime(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root / "run-2",
                env=env,
            )
            second_report = json.loads(
                Path(second["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )

            skeleton = second_report["stages"][0]
            deep_interview = second_report["stages"][1]
            execute_stage = second_report["stages"][4]

            self.assertGreaterEqual(len(skeleton["read_actions"]), 2)
            self.assertEqual("backend_read", skeleton["read_actions"][1]["status"])
            self.assertGreaterEqual(skeleton["read_actions"][1]["item_count"], 1)

            self.assertEqual("backend_read", deep_interview["read_actions"][0]["status"])
            self.assertGreaterEqual(deep_interview["read_actions"][0]["item_count"], 1)

            self.assertGreaterEqual(len(execute_stage["read_actions"]), 1)
            self.assertEqual("backend_read", execute_stage["read_actions"][0]["status"])
            self.assertGreaterEqual(execute_stage["read_actions"][0]["item_count"], 1)

            requirement_text = Path(second["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            self.assertIn("## Memory Context", requirement_text)
            self.assertIn("Serena decision:", requirement_text)

            plan_text = Path(second["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            self.assertIn("## Memory Context", plan_text)
            self.assertIn("Cognee relation:", plan_text)

    def test_runtime_hard_fails_when_workspace_broker_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            payload, run_id = run_governed_runtime_with_metadata(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root,
                env={"VIBE_MEMORY_BACKEND_DRIVER_MODE": "legacy"},
                check=False,
            )

            report_path = (
                temp_root
                / "outputs"
                / "runtime"
                / "vibe-sessions"
                / run_id
                / "memory-activation"
                / "memory-activation-report.json"
            )

            self.assertNotEqual(0, payload["returncode"])
            self.assertTrue(report_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            failed_statuses = {
                action["status"]
                for stage in report["stages"]
                for action in [*stage.get("read_actions", []), *stage.get("write_actions", [])]
                if "failed" in str(action.get("status") or "")
            }
            self.assertIn("memory_backend_invocation_failed", failed_statuses)

    def test_runtime_helper_keeps_native_specialist_disabled_when_caller_env_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            payload = run_governed_runtime(
                "I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
                artifact_root=temp_root / "runtime",
                env={
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_CODEX_EXECUTABLE": str(create_fake_codex_command(temp_root)),
                },
            )

            execution_manifest = json.loads(
                Path(payload["summary"]["artifacts"]["execution_manifest"]).read_text(encoding="utf-8")
            )
            execution_proof = json.loads(
                Path(payload["summary"]["artifacts"]["execution_proof_manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                "explicitly_degraded",
                execution_manifest["specialist_accounting"]["effective_execution_status"],
            )

            for result_path in execution_proof["result_paths"]:
                result = json.loads(Path(result_path).read_text(encoding="utf-8"))
                if result.get("kind") != "specialist_dispatch":
                    continue
                self.assertFalse(bool(result["live_native_execution"]))
                self.assertNotEqual("codex_exec_native_specialist", result["execution_driver"])


if __name__ == "__main__":
    unittest.main()
