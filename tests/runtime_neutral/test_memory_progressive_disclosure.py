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


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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
    complete_agent_handoff: bool = False,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-memory-disclosure-" + uuid.uuid4().hex[:10]
    workflow_level = "XL" if "XL" in task else "L"
    host_decision_json = json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": workflow_level,
                "modules": [
                    {
                        "module_id": "memory_runtime",
                        "goal": "Exercise governed memory disclosure behavior.",
                        "candidate_skill_ids": [],
                        "required": True,
                        "depends_on": [],
                        "execution_mode": "agent_direct",
                        "write_scope": "no task-file writes",
                        "expected_outputs": ["A governed memory disclosure result."],
                        "verification": ["Confirm the runtime emits the expected memory disclosure metadata."],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "memory-disclosure-result",
                                "description": "The governed memory disclosure is verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [],
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
        f"-WorkspaceRoot {_ps_single_quote(str(workspace_root))} "
        if workspace_root is not None
        else ""
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
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}' "
            f"{workspace_root_argument}"
            f"-HostDecisionJson {_ps_single_quote(host_decision_json)}; "
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
    if not complete_agent_handoff:
        return payload
    return complete_module_execution(
        payload,
        task=task,
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        env=effective_env,
    )


def complete_module_execution(
    payload: dict[str, object],
    *,
    task: str,
    artifact_root: Path,
    workspace_root: Path | None,
    env: dict[str, str],
) -> dict[str, object]:
    handoff = json.loads(
        Path(payload["summary"]["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8")
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
        unit["result_summary"] = "The Agent completed the approved memory-disclosure module."
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
            "covered_code_task_tdd_exceptions": list(tdd_contract["required_code_task_tdd_exceptions"]),
            "notes": "The simulated Agent completed the frozen TDD contract.",
        }
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    workspace_root_argument = (
        f"-WorkspaceRoot {_ps_single_quote(str(workspace_root))} "
        if workspace_root is not None
        else ""
    )
    command = [
        resolve_powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_single_quote(str(script_path))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(str(payload['run_id']))} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
            f"{workspace_root_argument}"
            "-RequestedStageStop phase_cleanup "
            f"-ModuleExecutionJsonFile {_ps_single_quote(str(module_execution_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout.strip())


def run_write_requirement_doc(
    task: str,
    artifact_root: Path,
    *,
    memory_context_path: Path | None = None,
    runtime_input_packet_path: Path | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
    run_id = "pytest-write-requirement-" + uuid.uuid4().hex[:10]
    ps_command = (
        "& { "
        f"$result = & {_ps_single_quote(str(script_path))} "
        f"-Task {_ps_single_quote(task)} "
        "-Mode interactive_governed "
        f"-RunId {_ps_single_quote(run_id)} "
        f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
    )
    if memory_context_path is not None:
        ps_command += f"-MemoryContextPath {_ps_single_quote(str(memory_context_path))} "
    if runtime_input_packet_path is not None:
        ps_command += f"-RuntimeInputPacketPath {_ps_single_quote(str(runtime_input_packet_path))} "
    ps_command += "$result | ConvertTo-Json -Depth 20 }"

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout not in ("", "null"):
        return json.loads(stdout)

    receipt_path = artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id / "requirement-doc-receipt.json"
    if not receipt_path.exists():
        raise AssertionError(
            "Write-RequirementDoc returned null payload and did not emit a receipt. "
            f"stderr={completed.stderr.strip()}"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "requirement_doc_path": receipt["requirement_doc_path"],
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


def run_write_xl_plan(
    task: str,
    artifact_root: Path,
    *,
    requirement_doc_path: Path,
    plan_memory_context_path: Path | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1"
    run_id = "pytest-write-plan-" + uuid.uuid4().hex[:10]
    runtime_input_packet_path = artifact_root / "runtime-input-packet.json"
    runtime_input_packet_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_input_packet_path.write_text(
        json.dumps(
            {
                "agent_skill_organization": {
                    "schema_version": "agent_skill_organization_v1",
                    "derived_by": "agent",
                    "workflow_level": "L",
                    "modules": [
                        {
                            "module_id": "memory_plan",
                            "goal": "Render memory disclosure in the execution plan.",
                            "candidate_skill_ids": [],
                            "execution_mode": "blocked_gap",
                            "acceptance_criteria": [
                                {
                                    "criterion_id": "memory-plan-rendered",
                                    "description": "The plan renders the approved memory disclosure.",
                                    "verification_mode": "automated",
                                }
                            ],
                        }
                    ],
                    "selected_skills": [],
                    "uncovered_modules": [
                        {
                            "module_id": "memory_plan",
                            "reason": "No task skill is required for this memory-plan test.",
                        }
                    ],
                    "workflow_level_contract": {
                        "L": "Use one bounded serial lane.",
                        "XL": "Use bounded parallel lanes with governed review.",
                    },
                },
                "module_assignments": {"units": []},
                "host_adapter": {
                    "effective_host_id": "codex",
                    "target_root": str(artifact_root / ".agents"),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ps_command = (
        "& { "
        f"$result = & {_ps_single_quote(str(script_path))} "
        f"-Task {_ps_single_quote(task)} "
        "-Mode interactive_governed "
        f"-RunId {_ps_single_quote(run_id)} "
        f"-RequirementDocPath {_ps_single_quote(str(requirement_doc_path))} "
        f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
        f"-RuntimeInputPacketPath {_ps_single_quote(str(runtime_input_packet_path))} "
    )
    if plan_memory_context_path is not None:
        ps_command += f"-PlanMemoryContextPath {_ps_single_quote(str(plan_memory_context_path))} "
    ps_command += "$result | ConvertTo-Json -Depth 20 }"

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout not in ("", "null"):
        return json.loads(stdout)

    receipt_path = artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id / "execution-plan-receipt.json"
    if not receipt_path.exists():
        raise AssertionError(
            "Write-XlPlan returned null payload and did not emit a receipt. "
            f"stderr={completed.stderr.strip()}"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "execution_plan_path": receipt["execution_plan_path"],
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


def run_selected_memory_capsules(read_actions: list[dict[str, object]]) -> list[dict[str, object]]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    memory_common = REPO_ROOT / "scripts" / "runtime" / "VibeMemoryActivation.Common.ps1"
    read_actions_json = json.dumps(read_actions, ensure_ascii=False)
    ps_command = (
        "& { "
        f". {_ps_single_quote(str(memory_common))}; "
        f"$readActions = {_ps_single_quote(read_actions_json)} | ConvertFrom-Json -Depth 20; "
        "$result = New-VibeSelectedMemoryCapsules "
        "-ReadActions @($readActions) "
        "-Budget ([pscustomobject]@{ top_k = 2; max_tokens = 32; max_chars_per_item = 64 }) "
        "-Stage 'requirement_doc'; "
        "$result | ConvertTo-Json -Depth 20 }"
    )

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    return payload if isinstance(payload, list) else [payload]


def run_progressive_disclosure_context_pack(
    *,
    session_root: Path,
    read_actions: list[dict[str, object]],
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    runtime_common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    memory_common = REPO_ROOT / "scripts" / "runtime" / "VibeMemoryActivation.Common.ps1"
    runtime_entry = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    read_actions_json = json.dumps(read_actions, ensure_ascii=False)
    ps_command = (
        "& { "
        f". {_ps_single_quote(str(runtime_common))}; "
        f". {_ps_single_quote(str(memory_common))}; "
        f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(runtime_entry))}; "
        "$runtime.memory_retrieval_budget_policy.defaults.top_k = 2; "
        "$runtime.memory_retrieval_budget_policy.defaults.max_tokens = 4; "
        "$runtime.memory_retrieval_budget_policy.defaults.max_chars_per_item = 64; "
        "$runtime.memory_retrieval_budget_policy.stages.requirement_doc.top_k = 2; "
        "$runtime.memory_retrieval_budget_policy.stages.requirement_doc.max_tokens = 4; "
        "$runtime.memory_retrieval_budget_policy.stages.requirement_doc.max_chars_per_item = 64; "
        "$runtime.memory_disclosure_policy.defaults.max_capsules = 2; "
        "$runtime.memory_disclosure_policy.defaults.max_chars_per_capsule = 64; "
        "$runtime.memory_disclosure_policy.stages.requirement_doc = "
        "[pscustomobject]@{ level = 'decision_focused'; max_capsules = 2; max_chars_per_capsule = 64 }; "
        f"$readActions = {_ps_single_quote(read_actions_json)} | ConvertFrom-Json -Depth 20; "
        "$result = New-VibeProgressiveDisclosureContextPack "
        "-Runtime $runtime "
        "-ReadActions @($readActions) "
        f"-SessionRoot {_ps_single_quote(str(session_root))} "
        "-Stage 'requirement_doc' "
        "-ArtifactName 'progressive-pack.json'; "
        "$result | ConvertTo-Json -Depth 20 }"
    )

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


class MemoryProgressiveDisclosureTests(unittest.TestCase):
    def test_related_runs_emit_capsule_metadata_before_agent_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            env = {
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "backends"),
                "SERENA_PROJECT_KEY": "pytest-memory-disclosure-project",
            }
            workspace_root = temp_root / "workspace"

            run_governed_runtime(
                "XL approved decision: keep api worker runtime continuity and graph relationship between api worker and planner.",
                artifact_root=temp_root / "seed-run",
                env=env,
                workspace_root=workspace_root,
                complete_agent_handoff=True,
            )
            second = run_governed_runtime(
                "XL follow-up api worker continuity review with decision reuse and graph dependency recall.",
                artifact_root=temp_root / "follow-up-run",
                env=env,
                workspace_root=workspace_root,
            )

            summary = second["summary"]
            requirement_receipt = json.loads(
                Path(summary["artifacts"]["requirement_receipt"]).read_text(encoding="utf-8")
            )
            plan_receipt = json.loads(
                Path(summary["artifacts"]["execution_plan_receipt"]).read_text(encoding="utf-8")
            )
            requirement_context = json.loads(
                Path(requirement_receipt["memory_context_path"]).read_text(encoding="utf-8")
            )
            plan_context = json.loads(
                Path(plan_receipt["plan_memory_context_path"]).read_text(encoding="utf-8")
            )
            context_paths = {
                "requirement_doc": Path(requirement_receipt["memory_context_path"]),
                "xl_plan": Path(plan_receipt["plan_memory_context_path"]),
            }

            self.assertEqual(
                DISCLOSURE_POLICY["stages"]["requirement_doc"]["level"],
                requirement_context["disclosure_level"],
            )
            self.assertEqual(
                DISCLOSURE_POLICY["stages"]["xl_plan"]["level"],
                plan_context["disclosure_level"],
            )
            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertIsNotNone(summary["artifacts"]["agent_execution_handoff"])
            self.assertIsNone(summary["artifacts"]["memory_activation_report"])

            for stage_name, context in (
                ("requirement_doc", requirement_context),
                ("xl_plan", plan_context),
            ):
                with self.subTest(context=context["disclosure_level"]):
                    self.assertLessEqual(
                        context["capsule_count"],
                        DISCLOSURE_POLICY["stages"][stage_name]["max_capsules"],
                    )
                    self.assertGreaterEqual(context["capsule_count"], 1)
                    self.assertTrue(context_paths[stage_name].exists())
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
            workspace_root = temp_root / "workspace"

            run_governed_runtime(
                "Approved decision: reuse bounded memory capsules for release planning and execution evidence.",
                artifact_root=temp_root / "seed-run",
                env=env,
                workspace_root=workspace_root,
                complete_agent_handoff=True,
            )
            second = run_governed_runtime(
                "Plan the next release using bounded memory capsules and prior execution evidence.",
                artifact_root=temp_root / "follow-up-run",
                env=env,
                workspace_root=workspace_root,
            )

            requirement_text = Path(second["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            plan_text = Path(second["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            requirement_receipt = json.loads(
                Path(second["summary"]["artifacts"]["requirement_receipt"]).read_text(encoding="utf-8")
            )
            plan_receipt = json.loads(
                Path(second["summary"]["artifacts"]["execution_plan_receipt"]).read_text(encoding="utf-8")
            )

            self.assertNotIn("## Memory Context", requirement_text)
            self.assertNotIn("Capsule", requirement_text)
            self.assertNotIn("Expansion Ref", requirement_text)
            self.assertNotIn("## Memory Context", plan_text)
            self.assertNotIn("Capsule", plan_text)
            self.assertNotIn("Expansion Ref", plan_text)
            self.assertGreaterEqual(requirement_receipt["memory_capsule_count"], 1)
            self.assertTrue(bool(requirement_receipt["memory_context_path"]))
            self.assertGreaterEqual(plan_receipt["plan_memory_capsule_count"], 1)
            self.assertTrue(bool(plan_receipt["plan_memory_context_path"]))

    def test_selected_memory_capsules_do_not_require_ambient_stage_scope(self) -> None:
        capsules = run_selected_memory_capsules(
            [
                {
                    "owner": "Serena",
                    "items": ["Quartz scheduler continuity"],
                    "capsules": [
                        {
                            "capsule_id": "cap-ambient-stage",
                            "owner": "Serena",
                            "lane": "serena",
                            "kind": "decision",
                            "summary": "Quartz scheduler continuity",
                            "updated_at": "2026-04-10T00:00:00Z",
                        }
                    ],
                    "artifact_path": str(REPO_ROOT / "docs" / "design" / "workspace-memory-plane.md"),
                }
            ]
        )

        self.assertEqual(1, len(capsules))
        self.assertEqual("cap-ambient-stage", capsules[0]["capsule_id"])

    def test_progressive_disclosure_only_reports_capsules_that_fit_bounded_items(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            read_actions = [
                {
                    "owner": "Serena",
                    "status": "backend_read",
                    "items": [
                        "abcdefghijklmnop",
                        "qrstuvwxyzabcdefgh",
                    ],
                    "capsules": [
                        {
                            "capsule_id": "cap-one",
                            "owner": "Serena",
                            "lane": "serena",
                            "kind": "decision",
                            "summary": "abcdefghijklmnop",
                            "updated_at": "2026-04-10T00:00:00Z",
                        },
                        {
                            "capsule_id": "cap-two",
                            "owner": "Serena",
                            "lane": "serena",
                            "kind": "decision",
                            "summary": "qrstuvwxyzabcdefgh",
                            "updated_at": "2026-04-10T00:00:01Z",
                        },
                    ],
                    "artifact_path": str(temp_root / "backend-response.json"),
                }
            ]

            result = run_progressive_disclosure_context_pack(
                session_root=temp_root / "session",
                read_actions=read_actions,
            )
            artifact = json.loads(Path(result["context_path"]).read_text(encoding="utf-8"))

            self.assertEqual(1, result["injected_item_count"])
            self.assertEqual(1, result["capsule_count"])
            self.assertEqual(1, len(result["selected_capsules"]))
            self.assertEqual(["abcdefghijklmnop"], result["items"])
            self.assertEqual("cap-one", result["selected_capsules"][0]["capsule_id"])
            self.assertEqual(1, artifact["capsule_count"])
            self.assertEqual(1, len(artifact["selected_capsules"]))
            self.assertEqual("cap-one", artifact["selected_capsules"][0]["capsule_id"])

    def test_requirement_and_plan_docs_render_capsules_even_when_items_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            context_path = temp_root / "capsule-only-pack.json"
            context_path.write_text(
                json.dumps(
                    {
                        "disclosure_level": "decision_focused",
                        "selected_capsules": [
                            {
                                "capsule_id": "cap-001",
                                "title": "Quartz scheduler continuity",
                                "owner": "Serena",
                                "lane": "serena",
                                "kind": "decision",
                                "why_now": "Matched Serena memory for requirement_doc.",
                                "expansion_ref": f"{temp_root / 'backend-response.json'}#cap-001",
                                "summary_lines": ["Quartz scheduler continuity"],
                                "updated_at": "2026-04-10T00:00:00Z",
                            }
                        ],
                        "items": [],
                        "estimated_tokens": 1,
                        "budget": {"top_k": 2, "max_tokens": 32, "max_chars_per_item": 200},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            requirement = run_write_requirement_doc(
                "Plan quartz scheduler continuity reuse.",
                temp_root / "requirement-artifacts",
                memory_context_path=context_path,
            )
            plan = run_write_xl_plan(
                "Plan quartz scheduler continuity reuse.",
                temp_root / "plan-artifacts",
                requirement_doc_path=Path(requirement["requirement_doc_path"]),
                plan_memory_context_path=context_path,
            )

            requirement_text = Path(requirement["requirement_doc_path"]).read_text(encoding="utf-8")
            plan_text = Path(plan["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertNotIn("## Memory Context", requirement_text)
            self.assertNotIn("Capsule [cap-001] Quartz scheduler continuity", requirement_text)
            self.assertNotIn("Expansion Ref", requirement_text)
            self.assertNotIn("## Memory Context", plan_text)
            self.assertNotIn("Capsule [cap-001] Quartz scheduler continuity", plan_text)
            self.assertNotIn("Expansion Ref", plan_text)
            self.assertEqual(1, requirement["receipt"]["memory_capsule_count"])
            self.assertEqual(str(context_path), requirement["receipt"]["memory_context_path"])
            self.assertEqual(1, plan["receipt"]["plan_memory_capsule_count"])
            self.assertEqual(str(context_path), plan["receipt"]["plan_memory_context_path"])

    def test_requirement_and_plan_receipts_treat_null_selected_capsules_as_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            context_path = temp_root / "null-capsules-pack.json"
            context_path.write_text(
                json.dumps(
                    {
                        "disclosure_level": "decision_focused",
                        "selected_capsules": None,
                        "items": [],
                        "estimated_tokens": 0,
                        "budget": {"top_k": 2, "max_tokens": 32, "max_chars_per_item": 200},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            requirement = run_write_requirement_doc(
                "Plan null capsule count handling.",
                temp_root / "requirement-null-artifacts",
                memory_context_path=context_path,
            )
            plan = run_write_xl_plan(
                "Plan null capsule count handling.",
                temp_root / "plan-null-artifacts",
                requirement_doc_path=Path(requirement["requirement_doc_path"]),
                plan_memory_context_path=context_path,
            )

            self.assertEqual(0, requirement["receipt"]["memory_capsule_count"])
            self.assertEqual(0, plan["receipt"]["plan_memory_capsule_count"])


if __name__ == "__main__":
    unittest.main()
