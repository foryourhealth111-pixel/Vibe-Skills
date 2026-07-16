from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


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


def run_governed_runtime(
    task: str,
    artifact_root: Path,
    env: dict[str, str] | None = None,
    *,
    workspace_root: Path | None = None,
    agent_skill_ids: list[str] | None = None,
    workflow_level: str = "L",
    complete_agent_handoff: bool = False,
) -> dict[str, object]:
    payload, _ = run_governed_runtime_with_metadata(
        task,
        artifact_root,
        env=env,
        workspace_root=workspace_root,
        agent_skill_ids=agent_skill_ids,
        workflow_level=workflow_level,
        complete_agent_handoff=complete_agent_handoff,
    )
    return payload


def run_governed_runtime_with_metadata(
    task: str,
    artifact_root: Path,
    env: dict[str, str] | None = None,
    *,
    workspace_root: Path | None = None,
    agent_skill_ids: list[str] | None = None,
    workflow_level: str = "L",
    complete_agent_handoff: bool = False,
) -> tuple[dict[str, object], str]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-memory-runtime-" + uuid.uuid4().hex[:10]
    selected_skill_ids = list(agent_skill_ids or [])
    host_decision_json = json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": workflow_level,
                "modules": [
                    {
                        "module_id": "memory_runtime",
                        "goal": "Exercise governed memory activation behavior.",
                        "candidate_skill_ids": selected_skill_ids,
                        "execution_mode": "skill_assigned" if selected_skill_ids else "agent_direct",
                        "write_scope": "no task-file writes",
                        "expected_outputs": ["A governed memory activation report."],
                        "verification": ["Confirm the runtime report records the expected stage-aware memory behavior."],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "memory-runtime-observed",
                                "description": "The governed memory activation result is present.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [
                    {
                        "skill_id": skill_id,
                        "module_ids": ["memory_runtime"],
                        "role": "owner",
                        "responsibility": f"Own the bounded {skill_id} work.",
                        "reason": f"The Agent reviewed {skill_id}/SKILL.md and selected it for this test.",
                        "write_scope": "no task-file writes",
                        "expected_outputs": ["A governed memory activation report."],
                        "verification": ["Confirm the runtime report records the expected stage-aware memory behavior."],
                    }
                    for skill_id in selected_skill_ids
                ],
                "uncovered_modules": [],
                "workflow_level_contract": {
                    "L": "Use one bounded serial lane.",
                    "XL": "Use bounded parallel lanes with governed review.",
                },
            }
        },
        separators=(",", ":"),
    )
    workspace_root_argument = (
        f"-WorkspaceRoot {ps_quote(workspace_root)} " if workspace_root is not None else ""
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {ps_quote(script_path)} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"{workspace_root_argument}"
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
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
    payload = json.loads(stdout)
    if complete_agent_handoff:
        payload = complete_module_execution(
            payload,
            task=task,
            artifact_root=artifact_root,
            env=effective_env,
            workspace_root=workspace_root,
        )
    return payload, run_id


def complete_module_execution(
    payload: dict[str, object],
    *,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    workspace_root: Path | None = None,
) -> dict[str, object]:
    handoff = json.loads(
        Path(payload["summary"]["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    result_contract = handoff["result_contract"]
    module_execution_path = Path(handoff["module_execution_path"])
    module_execution = json.loads(json.dumps(result_contract["submission_template"]))
    criteria_by_module = {
        str(module["module_id"]): [
            {**criterion, "state": "passing"}
            for criterion in module["criterion_results"]
        ]
        for module in module_execution["modules"]
    }
    for unit in module_execution["units"]:
        unit["state"] = "completed"
        unit["result_summary"] = "The Agent completed the approved memory-runtime module."
        unit["verification_results"] = criteria_by_module[str(unit["module_id"])]
    for module in module_execution["modules"]:
        module["state"] = "completed"
        module["criterion_results"] = criteria_by_module[str(module["module_id"])]
    if "tdd_evidence" in module_execution:
        tdd_contract = result_contract["tdd_evidence"]
        required_tdd = list(tdd_contract["required_code_task_tdd_evidence_requirements"])
        evidence_path = str(module_execution_path)
        module_execution["tdd_evidence"] = {
            "state": "passing",
            "evidence_paths": [evidence_path],
            "red_phase_evidence_paths": [evidence_path] if required_tdd else [],
            "green_phase_evidence_paths": [evidence_path] if required_tdd else [],
            "refactor_phase_evidence_paths": [],
            "covered_code_task_tdd_evidence_requirements": required_tdd,
            "covered_code_task_tdd_exceptions": list(
                tdd_contract["required_code_task_tdd_exceptions"]
            ),
            "notes": "The simulated Agent completed the frozen TDD contract.",
        }
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")
    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    workspace_root_argument = (
        f"-WorkspaceRoot {ps_quote(workspace_root)} " if workspace_root is not None else ""
    )
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "& { "
                f"$result = & {ps_quote(script_path)} "
                f"-Task {ps_quote(task)} "
                "-Mode interactive_governed "
                f"-RunId {ps_quote(payload['run_id'])} "
                f"-ArtifactRoot {ps_quote(artifact_root)} "
                f"{workspace_root_argument}"
                "-RequestedStageStop phase_cleanup "
                f"-ModuleExecutionJsonFile {ps_quote(module_execution_path)}; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout.strip())


class MemoryRuntimeActivationTests(unittest.TestCase):
    def test_runtime_activation_report_keeps_required_stage_shape_and_owner_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_governed_runtime(
                "Audit current governed memory activation contracts before refactoring shared memory.",
                artifact_root=Path(tempdir),
                complete_agent_handoff=True,
            )
            report = json.loads(
                Path(payload["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )

            stages = report["stages"]
            self.assertEqual(6, len(stages))

            stage_by_name = {stage["stage"]: stage for stage in stages}
            stage_policy = json.loads(
                (REPO_ROOT / "config" / "memory-stage-activation-policy.json").read_text(encoding="utf-8")
            )
            expected_read_owners = {
                stage["stage"]: {action["owner"].casefold() for action in stage["read_actions"]}
                for stage in stage_policy["stages"]
            }
            expected_write_owners = {
                stage["stage"]: {action["owner"].casefold() for action in stage["write_actions"]}
                for stage in stage_policy["stages"]
            }
            self.assertEqual(
                expected_read_owners["skeleton_check"],
                {action["owner"].casefold() for action in stage_by_name["skeleton_check"]["read_actions"]},
            )
            self.assertEqual(
                expected_read_owners["xl_plan"],
                {action["owner"].casefold() for action in stage_by_name["xl_plan"]["read_actions"]},
            )
            self.assertEqual(
                expected_write_owners["plan_execute"],
                {action["owner"].casefold() for action in stage_by_name["plan_execute"]["write_actions"]},
            )
            self.assertEqual(
                expected_write_owners["phase_cleanup"],
                {action["owner"].casefold() for action in stage_by_name["phase_cleanup"]["write_actions"]},
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
                complete_agent_handoff=True,
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
            state_store_action = next(
                action for action in skeleton["read_actions"] if action["owner"].casefold() == "state_store"
            )
            self.assertIn(state_store_action["status"], {"fallback_local_digest", "backend_read"})
            if "items" in state_store_action:
                self.assertLessEqual(
                    len(state_store_action["items"]),
                    state_store_action["budget"]["top_k"],
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
            workspace_root = temp_root / "workspace"

            first = run_governed_runtime(
                "XL approved decision: keep api worker runtime continuity and graph relationship between api worker and planner.",
                artifact_root=temp_root / "run-1",
                env=env,
                workspace_root=workspace_root,
                workflow_level="XL",
                complete_agent_handoff=True,
            )
            first_report = json.loads(
                Path(first["summary"]["artifacts"]["memory_activation_report"]).read_text(encoding="utf-8")
            )
            first_execute = first_report["stages"][4]
            first_cleanup = first_report["stages"][5]

            self.assertEqual("backend_write", first_execute["write_actions"][1]["status"])
            self.assertEqual("backend_write", first_cleanup["write_actions"][0]["status"])
            self.assertEqual("backend_write", first_cleanup["write_actions"][2]["status"])
            self.assertIn("workspace_memory_plane", first_execute["write_actions"][1])
            self.assertIn("workspace_id", first_execute["write_actions"][1]["workspace_memory_plane"])
            self.assertEqual("workspace_plane", first_execute["write_actions"][1]["project_key_source"])

            second = run_governed_runtime(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root / "run-2",
                env=env,
                workspace_root=workspace_root,
                workflow_level="XL",
                complete_agent_handoff=True,
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
            self.assertIn("workspace_memory_plane", skeleton["read_actions"][1])
            self.assertIn("workspace_id", skeleton["read_actions"][1]["workspace_memory_plane"])
            self.assertEqual("workspace_plane", skeleton["read_actions"][1]["project_key_source"])

            self.assertEqual("backend_read", deep_interview["read_actions"][0]["status"])
            self.assertGreaterEqual(deep_interview["read_actions"][0]["item_count"], 1)

            self.assertGreaterEqual(len(execute_stage["read_actions"]), 1)
            self.assertEqual("backend_read", execute_stage["read_actions"][0]["status"])
            self.assertGreaterEqual(execute_stage["read_actions"][0]["item_count"], 1)

            requirement_text = Path(second["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            requirement_receipt = json.loads(
                Path(second["summary"]["artifacts"]["requirement_receipt"]).read_text(encoding="utf-8")
            )
            self.assertNotIn("## Memory Context", requirement_text)
            self.assertGreaterEqual(requirement_receipt["memory_capsule_count"], 1)
            self.assertTrue(bool(requirement_receipt["memory_context_path"]))

            plan_text = Path(second["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            plan_receipt = json.loads(
                Path(second["summary"]["artifacts"]["execution_plan_receipt"]).read_text(encoding="utf-8")
            )
            self.assertNotIn("## Memory Context", plan_text)
            self.assertGreaterEqual(plan_receipt["plan_memory_capsule_count"], 1)
            self.assertTrue(bool(plan_receipt["plan_memory_context_path"]))

    def test_runtime_records_backend_failures_when_workspace_broker_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            payload, run_id = run_governed_runtime_with_metadata(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root,
                env={"VIBE_MEMORY_BACKEND_DRIVER_MODE": "legacy"},
                workflow_level="XL",
                complete_agent_handoff=True,
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

            self.assertEqual("phase_cleanup", payload["summary"]["terminal_stage"])
            self.assertTrue(report_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            failed_statuses = {
                action["status"]
                for stage in report["stages"]
                for action in [*stage.get("read_actions", []), *stage.get("write_actions", [])]
                if "failed" in str(action.get("status") or "")
            }
            self.assertIn("memory_backend_invocation_failed", failed_statuses)

    def test_runtime_uses_agent_handoff_even_when_a_host_executable_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root = temp_root / ".agents"
            skill_path = target_root / "skills" / "systematic-debugging" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(
                "---\nname: systematic-debugging\ndescription: Installed systematic-debugging test skill.\n---\n",
                encoding="utf-8",
            )
            payload = run_governed_runtime(
                "I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
                artifact_root=temp_root / "runtime",
                agent_skill_ids=["systematic-debugging"],
                env={
                    "VIBE_AGENTS_HOME": str(target_root),
                },
            )

            execution_manifest = json.loads(
                Path(payload["summary"]["artifacts"]["execution_manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                "agent_action_required",
                execution_manifest["module_handoff"]["status"],
            )
            handoff = json.loads(
                Path(payload["summary"]["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8")
            )
            self.assertEqual("agent_action_required", handoff["status"])
            self.assertEqual(["systematic-debugging"], [unit["skill_id"] for unit in handoff["units"]])
            self.assertEqual("plan_execute", payload["summary"]["terminal_stage"])
            self.assertIsNone(payload["summary"]["artifacts"]["cleanup_receipt"])
            self.assertIsNone(payload["summary"]["artifacts"]["memory_activation_report"])


if __name__ == "__main__":
    unittest.main()
