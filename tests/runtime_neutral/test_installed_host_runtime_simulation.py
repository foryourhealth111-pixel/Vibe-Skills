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
INSTALL_SCRIPT_SH = REPO_ROOT / "install.sh"
INSTALL_SCRIPT_PS1 = REPO_ROOT / "install.ps1"
TEST_SANDBOX_ROOT = Path(tempfile.gettempdir()) / "vibe-skills-pytest-installed-host-sim"
PLANNING_TASK = "Create a PRD and backlog for a small feature with quality gate requirements $vibe"
DEBUG_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes. $vibe"
EXECUTION_TASK = "Implement a bounded runtime enhancement with verification and cleanup $vibe"
MEMORY_TASK_FIRST = "Record that hidden skill topology must stay under vibe and planner depends on this decision. $vibe"
MEMORY_TASK_SECOND = "Follow up on the hidden skill topology decision and recall planner dependency before proposing the next step. $vibe"
SUPPORTED_CANONICAL_HOSTS = ("codex", "claude-code", "opencode")
HOST_HOME_ENV = {
    "codex": "VIBE_AGENTS_HOME",
    "claude-code": "VIBE_AGENTS_HOME",
    "cursor": "VIBE_AGENTS_HOME",
    "windsurf": "VIBE_AGENTS_HOME",
    "openclaw": "VIBE_AGENTS_HOME",
    "opencode": "VIBE_AGENTS_HOME",
}


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


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selected_skill_ids_from_runtime_input(runtime_input: dict[str, object]) -> list[str]:
    module_assignments = runtime_input.get("module_assignments")
    if not isinstance(module_assignments, dict):
        return []
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return []
    return [str(item.get("bound_skill") or "") for item in units if isinstance(item, dict) and str(item.get("bound_skill") or "")]


def write_installed_skill(target_root: Path, skill_id: str, *, name: str, description: str) -> Path:
    skill_path = target_root / "skills" / skill_id / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return skill_path


def install_host(target_root: Path, host_id: str, *, env: dict[str, str]) -> None:
    skills_dir = target_root / "skills"
    if os.name == "nt":
        shell = resolve_powershell()
        if shell is None:
            raise unittest.SkipTest("PowerShell executable not available in PATH")
        command = [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALL_SCRIPT_PS1),
            "-SkillsDir",
            str(skills_dir),
        ]
    else:
        command = [
            "bash",
            str(INSTALL_SCRIPT_SH),
            "--skills-dir",
            str(skills_dir),
        ]
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env=env,
    )


def run_installed_runtime(
    installed_root: Path,
    *,
    host_id: str,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    workspace_root: Path | None = None,
    agent_skill_ids: list[str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-installed-host-{host_id}-{uuid.uuid4().hex[:8]}"
    selected_skill_ids = list(agent_skill_ids or [])
    host_decision_json = json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "L",
                "modules": [
                    {
                        "module_id": "installed_host_work",
                        "goal": "Exercise the installed governed runtime.",
                        "candidate_skill_ids": selected_skill_ids,
                        "execution_mode": "skill_assigned" if selected_skill_ids else "blocked_gap",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "installed-host-result",
                                "description": "The installed governed runtime outcome is verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [
                    {
                        "skill_id": skill_id,
                        "module_ids": ["installed_host_work"],
                        "responsibility": f"Own the bounded {skill_id} work.",
                        "reason": f"The Agent reviewed {skill_id}/SKILL.md and selected it for this run.",
                    }
                    for skill_id in selected_skill_ids
                ],
                "uncovered_modules": []
                if selected_skill_ids
                else [
                    {
                        "module_id": "installed_host_work",
                        "reason": "No task skill is required for this installed-runtime memory test.",
                    }
                ],
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
            f"$result = & {ps_quote(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1')} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"{workspace_root_argument}"
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "installed invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def return_agent_module_execution(
    installed_root: Path,
    *,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    payload: dict[str, object],
    workspace_root: Path | None = None,
) -> dict[str, object]:
    summary = payload["summary"]
    artifacts = summary["artifacts"]
    if artifacts["module_execution"] is not None:
        raise AssertionError("plan_execute must not publish Agent execution results")

    handoff = load_json(artifacts["agent_execution_handoff"])
    module_execution_path = Path(handoff["module_execution_path"])
    if module_execution_path.exists():
        raise AssertionError("plan_execute must leave module-execution.json for the Agent")

    module_work_plan_path = Path(artifacts["module_work_plan"])
    module_work_plan = load_json(module_work_plan_path)
    result_contract = handoff["result_contract"]
    handoff_units = {
        str(unit["unit_id"]): unit
        for unit in handoff["units"]
    }
    criteria_by_module = {
        str(module["module_id"]): [
            {"criterion_id": str(criterion["criterion_id"]), "state": "passing"}
            for criterion in module.get("acceptance_criteria", [])
        ]
        for module in module_work_plan["modules"]
    }
    module_execution = json.loads(json.dumps(result_contract["submission_template"]))
    for unit in module_execution["units"]:
        handoff_unit = handoff_units[str(unit["unit_id"])]
        skill_entrypoint = handoff_unit["skill_entrypoint"]
        evidence_paths: list[str] = []
        if skill_entrypoint is not None:
            skill_path = Path(str(skill_entrypoint))
            if not skill_path.is_file():
                raise AssertionError(f"Agent handoff references missing SKILL.md: {skill_path}")
            evidence_paths = [str(skill_path)]
        unit["state"] = "completed"
        unit["result_summary"] = "The Agent completed the approved module work."
        unit["evidence_paths"] = evidence_paths
        unit["verification_results"] = criteria_by_module[str(unit["module_id"])]
    for module in module_execution["modules"]:
        blocked = module["execution_mode"] == "blocked_gap"
        module["state"] = "blocked" if blocked else "completed"
        for criterion in module["criterion_results"]:
            criterion["state"] = "blocked" if blocked else "passing"
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
            f"$result = & {ps_quote(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1')} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(payload['run_id'])} "
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"{workspace_root_argument}"
            "-RequestedStageStop phase_cleanup "
            f"-ModuleExecutionJsonFile {ps_quote(module_execution_path)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout.strip())


class InstalledHostRuntimeSimulationTests(unittest.TestCase):
    def _install_context(self, host_id: str) -> tuple[Path, Path, dict[str, str]]:
        TEST_SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        tempdir = tempfile.TemporaryDirectory(dir=str(TEST_SANDBOX_ROOT))
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        target_root = root / ".agents"
        target_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env[HOST_HOME_ENV[host_id]] = str(target_root)
        install_host(target_root, host_id, env=env)
        write_installed_skill(
            target_root,
            "feature-planning",
            name="PRD backlog quality gate",
            description="Create a PRD and backlog for a small feature with quality gate requirements.",
        )
        write_installed_skill(
            target_root,
            "systematic-debugging",
            name="failing test stack trace debug",
            description="Debug failing tests and stack traces with systematic root-cause analysis before proposing fixes.",
        )
        write_installed_skill(
            target_root,
            "runtime-enhancement-execution",
            name="bounded runtime enhancement verification cleanup",
            description="Implement bounded runtime enhancements with verification and cleanup.",
        )
        installed_root = target_root / "skills" / "vibe"
        self.assertTrue(installed_root.exists(), host_id)
        return target_root, installed_root, env

    def _assert_common_governed_outputs(
        self,
        payload: dict[str, object],
        *,
        host_id: str,
        allowed_execution_statuses: set[str] | None = None,
    ) -> dict[str, object]:
        summary = payload["summary"]
        artifacts = summary["artifacts"]
        runtime_input = load_json(artifacts["runtime_input_packet"])
        execution_manifest = load_json(artifacts["execution_manifest"])
        handoff = load_json(artifacts["agent_execution_handoff"])

        self.assertIn("route_snapshot", runtime_input, host_id)
        self.assertEqual("vibe", runtime_input["authority_flags"]["explicit_runtime_skill"], host_id)
        self.assertNotIn("runtime_selected_skill", runtime_input["divergence_shadow"], host_id)
        bound_skill_ids = [
            str(unit.get("bound_skill") or "")
            for unit in runtime_input["module_assignments"]["units"]
            if str(unit.get("bound_skill") or "")
        ]
        self.assertTrue(bound_skill_ids, host_id)
        self.assertNotIn("selected_skill", runtime_input["route_snapshot"], host_id)
        self.assertIn("skill_routing", runtime_input, host_id)
        self.assertNotIn("skill_usage", runtime_input, host_id)
        self.assertNotIn("specialist_decision", runtime_input, host_id)
        self.assertNotIn("legacy_skill_routing", runtime_input, host_id)
        self.assertNotIn("specialist_recommendations", runtime_input, host_id)
        self.assertNotIn("stage_assistant_hints", runtime_input, host_id)
        self.assertNotIn("specialist_dispatch", runtime_input, host_id)
        selected_skill_ids = selected_skill_ids_from_runtime_input(runtime_input)
        route_selected_skill = bound_skill_ids[0]
        if route_selected_skill != "vibe":
            self.assertIn(route_selected_skill, selected_skill_ids, host_id)
        self.assertTrue(Path(artifacts["requirement_doc"]).exists(), host_id)
        self.assertTrue(Path(artifacts["execution_plan"]).exists(), host_id)
        self.assertFalse((Path(summary["session_root"]) / "cleanup-receipt.json").exists(), host_id)
        allowed_statuses = allowed_execution_statuses or {"agent_action_required"}
        self.assertIn(execution_manifest["status"], allowed_statuses, host_id)
        self.assertEqual("agent_action_required", handoff["status"], host_id)
        self.assertIsNone(artifacts["module_execution"], host_id)
        self.assertFalse(Path(handoff["module_execution_path"]).exists(), host_id)
        return {
            "summary": summary,
            "artifacts": artifacts,
            "runtime_input": runtime_input,
            "handoff": handoff,
            "execution_manifest": execution_manifest,
        }

    def test_installed_hosts_support_high_fidelity_planning_debug_and_execution_tasks(self) -> None:
        for host_id in SUPPORTED_CANONICAL_HOSTS:
            with self.subTest(host=host_id):
                target_root, installed_root, base_env = self._install_context(host_id)
                runtime_env = {
                    **base_env,
                    "VCO_HOST_ID": host_id,
                }

                planning = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=PLANNING_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-planning",
                    env=runtime_env,
                    agent_skill_ids=["feature-planning"],
                )
                planning_state = self._assert_common_governed_outputs(
                    planning,
                    host_id=host_id,
                    allowed_execution_statuses={"agent_action_required"},
                )
                planning_requirement = Path(planning_state["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
                self.assertNotIn("## Runtime Input Truth", planning_requirement, host_id)
                self.assertIn("## Acceptance Criteria", planning_requirement, host_id)

                debug = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=DEBUG_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-debug",
                    env=runtime_env,
                    agent_skill_ids=["systematic-debugging"],
                )
                debug_state = self._assert_common_governed_outputs(debug, host_id=host_id)
                specialist_ids = selected_skill_ids_from_runtime_input(debug_state["runtime_input"])
                self.assertIn("systematic-debugging", specialist_ids, host_id)
                self.assertIn("systematic-debugging", [unit["skill_id"] for unit in debug_state["handoff"]["units"]], host_id)
                host_user_briefing_path = Path(debug_state["artifacts"]["host_user_briefing"])
                self.assertTrue(host_user_briefing_path.exists(), host_id)
                host_user_briefing = host_user_briefing_path.read_text(encoding="utf-8")
                self.assertEqual(
                    "agent_execution_handoff",
                    debug_state["summary"]["host_user_briefing"]["mode"],
                    host_id,
                )
                self.assertIn("Continue in this Agent turn", host_user_briefing, host_id)
                self.assertIn("systematic-debugging", host_user_briefing, host_id)
                self.assertIn("SKILL.md", host_user_briefing, host_id)

                execution = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=EXECUTION_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-execution",
                    env=runtime_env,
                    agent_skill_ids=["runtime-enhancement-execution"],
                )
                execution_state = self._assert_common_governed_outputs(execution, host_id=host_id)
                self.assertTrue(execution_state["handoff"]["units"], host_id)
                self.assertFalse(
                    Path(execution_state["handoff"]["module_execution_path"]).exists(),
                    host_id,
                )
                completed = return_agent_module_execution(
                    installed_root,
                    task=EXECUTION_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-execution",
                    env=runtime_env,
                    payload=execution,
                )
                completed_execution = load_json(completed["summary"]["artifacts"]["module_execution"])
                self.assertTrue(all(unit["state"] == "completed" for unit in completed_execution["units"]), host_id)
                self.assertTrue(Path(completed["summary"]["artifacts"]["cleanup_receipt"]).exists(), host_id)

    def test_installed_hosts_support_high_fidelity_memory_continuity(self) -> None:
        for host_id in SUPPORTED_CANONICAL_HOSTS:
            with self.subTest(host=host_id):
                target_root, installed_root, base_env = self._install_context(host_id)
                backend_root = target_root / ".vibeskills" / "memory-backend"
                runtime_env = {
                    **base_env,
                    "VCO_HOST_ID": host_id,
                    "SERENA_PROJECT_KEY": f"pytest-installed-{host_id}",
                    "VIBE_MEMORY_BACKEND_ROOT": str(backend_root),
                }

                first = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=MEMORY_TASK_FIRST,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-1",
                    env=runtime_env,
                    workspace_root=target_root / "workspace",
                )
                first = return_agent_module_execution(
                    installed_root,
                    task=MEMORY_TASK_FIRST,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-1",
                    env=runtime_env,
                    payload=first,
                    workspace_root=target_root / "workspace",
                )
                first_report = load_json(first["summary"]["artifacts"]["memory_activation_report"])
                self.assertGreaterEqual(len(first_report["stages"]), 5, host_id)
                self.assertTrue(first_report["stages"][4]["write_actions"], host_id)
                self.assertIn(
                    first_report["stages"][4]["write_actions"][0]["status"],
                    {"fallback_local_artifact", "backend_write"},
                    host_id,
                )

                second = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=MEMORY_TASK_SECOND,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-2",
                    env=runtime_env,
                    workspace_root=target_root / "workspace",
                )
                second = return_agent_module_execution(
                    installed_root,
                    task=MEMORY_TASK_SECOND,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-2",
                    env=runtime_env,
                    payload=second,
                    workspace_root=target_root / "workspace",
                )
                second_summary = second["summary"]
                second_report = load_json(second_summary["artifacts"]["memory_activation_report"])
                self.assertGreaterEqual(len(second_report["stages"]), 2, host_id)
                skeleton_reads = second_report["stages"][0]["read_actions"]
                deep_interview_reads = second_report["stages"][1]["read_actions"]
                later_reads = [
                    action
                    for stage in second_report["stages"][1:]
                    for action in stage.get("read_actions", [])
                ]
                self.assertTrue(any(action["status"] == "backend_read" for action in skeleton_reads), host_id)
                self.assertTrue(
                    any(action["status"] in {"backend_read", "backend_read_empty"} for action in deep_interview_reads),
                    host_id,
                )
                self.assertTrue(any(action["status"] == "backend_read" for action in later_reads), host_id)

                requirement_text = Path(second_summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
                plan_text = Path(second_summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
                requirement_receipt = load_json(second_summary["artifacts"]["requirement_receipt"])
                plan_receipt = load_json(second_summary["artifacts"]["execution_plan_receipt"])
                self.assertNotIn("## Memory Context", requirement_text, host_id)
                self.assertNotIn("## Memory Context", plan_text, host_id)
                self.assertGreaterEqual(int(requirement_receipt["memory_context_item_count"]), 1, host_id)
                self.assertGreaterEqual(int(requirement_receipt["memory_capsule_count"]), 1, host_id)
                self.assertTrue(bool(requirement_receipt["memory_context_path"]), host_id)
                self.assertGreaterEqual(int(plan_receipt["plan_memory_capsule_count"]), 1, host_id)
                self.assertTrue(bool(plan_receipt["plan_memory_context_path"]), host_id)


if __name__ == "__main__":
    unittest.main()
