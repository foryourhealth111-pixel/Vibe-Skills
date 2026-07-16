from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
for source_root in (
    REPO_ROOT / "packages" / "runtime-core" / "src",
    REPO_ROOT / "packages" / "contracts" / "src",
):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

import vgo_runtime.canonical_entry as canonical_entry


FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def prepare_local_skill_env(root: Path) -> dict[str, str]:
    agents_home = root / "home" / ".agents"
    skill_dir = agents_home / "skills" / "reentry-owner"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: reentry-owner\ndescription: Complete the approved re-entry module.\n---\n",
        encoding="utf-8",
    )
    return {**os.environ, "VCO_HOST_ID": "codex", "VIBE_AGENTS_HOME": str(agents_home)}


def build_reentry_agent_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [
            {
                "module_id": "reentry_module",
                "goal": "Produce the approved re-entry result.",
                "candidate_skill_ids": ["reentry-owner"],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "reentry-result",
                        "description": "The approved re-entry result is complete.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": "reentry-owner",
                "module_ids": ["reentry_module"],
                "responsibility": "Produce the approved re-entry result.",
                "reason": "Its SKILL.md owns this module.",
                "expected_outputs": ["outputs/reentry-result.md"],
                "verification": ["Confirm the result exists."],
            }
        ],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the approved module serially in the current Agent.",
            "XL": "Use bounded waves only for independent modules.",
        },
    }


def build_phase_decomposition_payload() -> dict[str, object]:
    return {
        "phases": [
            {
                "phase_id": "phase-requirement-refresh",
                "stage_order": 10,
                "stage_type": "planning",
                "stage_label": "Requirement Refresh",
                "goal": "Refresh the bounded requirement state before resuming work.",
                "acceptance_checks": ["bounded requirement context refreshed"],
            }
        ]
    }


def seed_previous_runtime_input_packet(artifact_root: Path) -> None:
    session_root = artifact_root / "outputs" / "runtime" / "vibe-sessions" / "prior-run"
    session_root.mkdir(parents=True, exist_ok=True)
    (session_root / "runtime-input-packet.json").write_text(
        json.dumps(
            {
                "run_id": "prior-run",
                "requested_stage_stop": "requirement_doc",
                "agent_skill_organization": {
                    "schema_version": "agent_skill_organization_v1",
                    "derived_by": "agent",
                    "workflow_level": "XL",
                    "modules": [
                        {
                            "module_id": "bounded_reentry",
                            "goal": "Resume the approved bounded workflow.",
                            "candidate_skill_ids": [],
                            "execution_mode": "blocked_gap",
                            "acceptance_criteria": [
                                {
                                    "criterion_id": "bounded-reentry-result",
                                    "description": "The approved bounded re-entry state is verified.",
                                    "verification_mode": "automated",
                                }
                            ],
                        }
                    ],
                    "selected_skills": [],
                    "uncovered_modules": [
                        {
                            "module_id": "bounded_reentry",
                            "reason": "The continuation contract test does not require a task-specific Skill.",
                        }
                    ],
                    "workflow_level_contract": {
                        "L": "Use one serial governed lane.",
                        "XL": "Use bounded waves when the approved organization needs them.",
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def build_host_decision_json() -> str:
    return json.dumps(
        {
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "phase_decomposition": build_phase_decomposition_payload(),
            "continuation_context": {
                "structured_bounded_reentry": True,
                "source_run_id": "prior-run",
                "terminal_stage": "requirement_doc",
                "next_stage": "xl_plan",
                "prior_task": "research ECG public datasets for diagnosis tasks",
                "prior_task_type": "research",
                "prior_goal": "research ECG public datasets for diagnosis tasks",
                "prior_deliverable": "Chinese report and dataset table",
                "prior_constraints": ["public-only", "official-source-only"],
                "control_only_prompt": True,
            },
        },
        ensure_ascii=False,
    )


def build_host_revision_decision_json() -> str:
    return json.dumps(
        {
            "decision_kind": "approval_response",
            "decision_action": "revise_requirement",
            "approval_decision": "revise",
            "phase_decomposition": build_phase_decomposition_payload(),
            "revision_delta": [
                "Add one public small/medium face dataset downloaded locally.",
                "Require a polished LaTeX paper and compiled PDF.",
            ],
            "continuation_context": {
                "structured_bounded_reentry": True,
                "reentry_action": "revise",
                "source_run_id": "prior-run",
                "terminal_stage": "requirement_doc",
                "next_stage": "xl_plan",
                "revision_target_stage": "requirement_doc",
                "revision_delta": [
                    "Add one public small/medium face dataset downloaded locally.",
                    "Require a polished LaTeX paper and compiled PDF.",
                ],
                "prior_task": "write a facial-recognition research paper",
                "prior_task_type": "research",
                "prior_goal": "write a facial-recognition research paper",
                "prior_deliverable": "LaTeX paper and compiled PDF",
                "prior_constraints": ["public-dataset", "local-download"],
                "control_only_prompt": True,
            },
        },
        ensure_ascii=False,
    )


def run_freeze(
    *,
    artifact_root: Path,
    host_decision_json: str,
    task: str = "批准",
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    seed_previous_runtime_input_packet(artifact_root)
    run_id = "pytest-structured-reentry-freeze-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            "$env:VCO_HOST_ID = 'codex'; "
            f"$result = & {ps_quote(str(FREEZE_SCRIPT))} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(str(artifact_root))} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
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
        env={**os.environ},
    )
    payload = json.loads(completed.stdout)
    if payload is None:
        raise AssertionError(
            "Freeze-RuntimeInputPacket.ps1 returned null. "
            f"stderr was: {completed.stderr.strip()}"
        )
    return payload


def run_runtime(
    *,
    artifact_root: Path,
    host_decision_json: str,
    requested_stage_stop: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    seed_previous_runtime_input_packet(artifact_root)
    run_id = "pytest-structured-reentry-runtime-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            "$env:VCO_HOST_ID = 'codex'; "
            f"$result = & {ps_quote(str(RUNTIME_SCRIPT))} "
            "-Task '批准' "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"{'-RequestedStageStop ' + ps_quote(requested_stage_stop) + ' ' if requested_stage_stop else ''}"
            f"-ArtifactRoot {ps_quote(str(artifact_root))} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
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
        env={**os.environ},
    )
    payload = json.loads(completed.stdout)
    if payload is None:
        raise AssertionError(
            "invoke-vibe-runtime.ps1 returned null. "
            f"stderr was: {completed.stderr.strip()}"
        )
    return payload


def run_common_script(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f". {ps_quote(str(REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1'))}; "
            f"{script} "
            "}"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    payload = json.loads(completed.stdout)
    if payload is None:
        raise AssertionError(
            "VibeRuntime.Common.ps1 helper returned null. "
            f"stderr was: {completed.stderr.strip()}"
        )
    return payload


class StructuredBoundedReentryContinuationTests(unittest.TestCase):
    def test_structured_revision_prompt_keeps_one_goal_and_one_revision_delta(self) -> None:
        prompt = canonical_entry._build_structured_continuation_prompt(
            prompt_text="请继续执行工作流。",
            continuation={
                "intent_goal": "研究 TRIZ 方法及其适用边界",
                "intent_deliverable": "Governed implementation artifacts, verification evidence, and cleanup receipts",
                "intent_constraints": ["follow the runtime workflow"],
                "revision_delta": ["交付一份中文 Word 综述报告"],
            },
        )

        self.assertEqual(
            "研究 TRIZ 方法及其适用边界 Revision delta: 交付一份中文 Word 综述报告.",
            prompt,
        )
        self.assertNotIn("Deliverable:", prompt)
        self.assertNotIn("Constraints:", prompt)
        self.assertNotIn("Update:", prompt)

    def test_invalid_phase_decomposition_fails_fast(self) -> None:
        payload = run_common_script(
            "try { "
            "$decision = [pscustomobject]@{ "
            "  phase_decomposition = [pscustomobject]@{ phases = @('oops') } "
            "}; "
            "Resolve-VibeHostPhaseDecomposition -HostDecision $decision -Task 'demo task' | Out-Null; "
            "@{ ok = $true } | ConvertTo-Json -Compress "
            "} catch { "
            "@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress "
            "} "
        )

        self.assertFalse(payload["ok"])
        self.assertIn("each execution phase must be a JSON object", payload["error"])

    def test_freeze_reuses_prior_task_type_for_control_only_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            payload = run_freeze(
                artifact_root=artifact_root,
                host_decision_json=build_host_decision_json(),
            )
            packet = payload["packet"]

            self.assertEqual("research", packet["route_snapshot"]["task_type"])
            self.assertTrue(packet["continuation_context"]["structured_bounded_reentry"])
            self.assertTrue(packet["continuation_context"]["control_only_prompt"])
            self.assertIn("phase_decomposition", packet["host_decision"])
            self.assertNotIn("decision_kind", packet["host_decision"])
            self.assertNotIn("decision_action", packet["host_decision"])
            self.assertNotIn("continuation_context", packet["host_decision"])
            self.assertNotIn("execution_phase_decomposition", packet)

    def test_refreeze_preserves_revision_delta_without_legacy_host_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            payload = run_freeze(
                artifact_root=artifact_root,
                host_decision_json=build_host_revision_decision_json(),
            )
            packet = payload["packet"]

            self.assertEqual("research", packet["route_snapshot"]["task_type"])
            self.assertEqual("revise", packet["continuation_context"]["reentry_action"])
            self.assertEqual("requirement_doc", packet["continuation_context"]["revision_target_stage"])
            self.assertEqual(
                [
                    "Add one public small/medium face dataset downloaded locally.",
                    "Require a polished LaTeX paper and compiled PDF.",
                ],
                packet["continuation_context"]["revision_delta"],
            )
            self.assertNotIn("decision_action", packet["host_decision"])
            self.assertNotIn("revision_delta", packet["host_decision"])
            self.assertNotIn("continuation_context", packet["host_decision"])
            self.assertNotIn("host_reentry_action", packet)
            self.assertNotIn("host_revision_target_stage", packet)
            self.assertNotIn("host_revision_delta", packet)

    def test_refreeze_keeps_research_type_when_revision_prompt_contains_governance_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            host_decision = json.loads(build_host_revision_decision_json())
            host_decision["revision_delta"] = [
                "交付一份中文 Word 综述报告。",
                "按批准的工作流继续完成来源核验与文档验收。",
            ]
            host_decision["continuation_context"]["revision_delta"] = host_decision["revision_delta"]
            host_decision["continuation_context"]["prior_task"] = "研究 TRIZ 方法及其适用边界"
            host_decision["continuation_context"]["prior_goal"] = "研究 TRIZ 方法及其适用边界"
            host_decision["continuation_context"]["prior_deliverable"] = "中文 Word 综述报告"
            host_decision["continuation_context"]["control_only_prompt"] = False

            payload = run_freeze(
                artifact_root=artifact_root,
                host_decision_json=json.dumps(host_decision, ensure_ascii=False),
                task=(
                    "研究 TRIZ 方法及其适用边界。Deliverable: Governed implementation artifacts, "
                    "verification evidence, and cleanup receipts. Constraints: follow the runtime "
                    "workflow. Revision delta: 交付一份中文 Word 综述报告。Update: 请继续执行工作流。"
                ),
            )
            packet = payload["packet"]

            self.assertFalse(packet["continuation_context"]["control_only_prompt"])
            self.assertEqual("research", packet["route_snapshot"]["task_type"])
            self.assertEqual("not_applicable", packet["code_task_tdd_decision"]["mode"])

    def test_canonical_reentry_reuses_the_frozen_agent_organization(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            artifact_root = root / "artifacts"
            env = prepare_local_skill_env(root)
            with mock.patch.dict(os.environ, env, clear=True):
                requirement_stop = canonical_entry.launch_canonical_vibe(
                    repo_root=REPO_ROOT,
                    host_id="codex",
                    entry_id="vibe",
                    prompt="Prepare the approved re-entry module.",
                    artifact_root=artifact_root,
                )
                plan_stop = canonical_entry.launch_canonical_vibe(
                    repo_root=REPO_ROOT,
                    host_id="codex",
                    entry_id="vibe",
                    prompt="Approve the requirement and prepare the plan.",
                    artifact_root=artifact_root,
                    continue_from_run_id=requirement_stop.run_id,
                    bounded_reentry_token=requirement_stop.summary[
                        "bounded_return_control"
                    ]["reentry_token"],
                    host_decision={
                        "decision_kind": "approval_response",
                        "decision_action": "approve_requirement",
                        "approval_decision": "approve",
                        "agent_skill_organization": build_reentry_agent_organization(),
                    },
                )
                handoff_stop = canonical_entry.launch_canonical_vibe(
                    repo_root=REPO_ROOT,
                    host_id="codex",
                    entry_id="vibe",
                    prompt="Approve the plan and execute it.",
                    artifact_root=artifact_root,
                    continue_from_run_id=plan_stop.run_id,
                    bounded_reentry_token=plan_stop.summary["bounded_return_control"][
                        "reentry_token"
                    ],
                    host_decision={
                        "decision_kind": "approval_response",
                        "decision_action": "approve_plan",
                        "approval_decision": "approve",
                    },
                )
            source_summary = handoff_stop.summary
            source_packet = json.loads(
                Path(source_summary["artifacts"]["runtime_input_packet"]).read_text(
                    encoding="utf-8"
                )
            )
            handoff = json.loads(
                Path(source_summary["artifacts"]["agent_execution_handoff"]).read_text(
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
                unit["result_summary"] = "Produced the approved re-entry result."
                unit["verification_results"] = criteria_by_module[str(unit["module_id"])]
            for module in module_execution["modules"]:
                module["state"] = "completed"
                module["criterion_results"] = criteria_by_module[str(module["module_id"])]
            module_execution_path.write_text(
                json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, env, clear=True):
                result = canonical_entry.launch_canonical_vibe(
                    repo_root=REPO_ROOT,
                    host_id="codex",
                    entry_id="vibe",
                    prompt="Continue after Agent module execution.",
                    artifact_root=artifact_root,
                    continue_from_run_id=source_summary["run_id"],
                    module_execution_json_file=module_execution_path,
                )
            reentered_packet = json.loads(
                Path(result.artifacts["runtime_input_packet"]).read_text(encoding="utf-8")
            )
            cleanup_receipt_exists = (result.session_root / "cleanup-receipt.json").exists()

        self.assertEqual(
            "agent_skill_organization_v1",
            source_packet["agent_skill_organization"]["schema_version"],
        )
        self.assertEqual("agent_execution_handoff_v1", handoff["schema_version"])
        self.assertEqual("agent_action_required", handoff["status"])
        self.assertEqual("module_execution_v1", module_execution["schema_version"])
        self.assertEqual("completed", module_execution["modules"][0]["state"])
        self.assertEqual(["reentry-owner"], [unit["skill_id"] for unit in handoff["units"]])
        self.assertEqual(source_summary["run_id"], result.run_id)
        self.assertEqual("phase_cleanup", result.summary["terminal_stage"])
        self.assertEqual(
            source_packet["agent_skill_organization"],
            reentered_packet["agent_skill_organization"],
        )
        self.assertEqual(
            source_summary["artifacts"]["module_work_plan"],
            result.summary["artifacts"]["module_work_plan"],
        )
        self.assertTrue(cleanup_receipt_exists)

    def test_runtime_stops_for_agent_execution_without_post_execution_memory_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            payload = run_runtime(
                artifact_root=artifact_root,
                host_decision_json=build_host_decision_json(),
                requested_stage_stop=None,
            )
            summary = payload["summary"]
            requirement_receipt = json.loads(
                Path(summary["artifacts"]["requirement_receipt"]).read_text(encoding="utf-8")
            )
            plan_receipt = json.loads(
                Path(summary["artifacts"]["execution_plan_receipt"]).read_text(encoding="utf-8")
            )

            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertIsNotNone(summary["artifacts"]["agent_execution_handoff"])
            self.assertIsNone(summary["artifacts"]["memory_activation_report"])
            self.assertIsNone(summary["memory_activation"])
            self.assertGreaterEqual(requirement_receipt["memory_context_item_count"], 1)
            self.assertGreaterEqual(requirement_receipt["memory_capsule_count"], 1)
            self.assertTrue(Path(plan_receipt["plan_memory_context_path"]).exists())


if __name__ == "__main__":
    unittest.main()
