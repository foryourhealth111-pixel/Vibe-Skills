from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from unittest import mock
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
RELEVANT_TOPIC = "quartz-scheduler"
RELEVANT_DEPENDENCY = "planner"
IRRELEVANT_TOPIC = "billing-export"
IRRELEVANT_DEPENDENCY = "audit-ledger"
RUN_MEMORY_BENCHMARKS_ENV = "VIBESKILLS_RUN_MEMORY_BENCHMARKS"
RUNTIME_INVOCATION_TIMEOUT_SECONDS = 240
INSTALL_TIMEOUT_SECONDS = 180


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _all_uncovered_host_decision_json() -> str:
    return json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "XL",
                "modules": [
                    {
                        "module_id": "memory_runtime_simulation",
                        "goal": "Exercise governed memory continuity without a task specialist.",
                        "candidate_skill_ids": [],
                        "execution_mode": "blocked_gap",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "memory-continuity-result",
                                "description": "Workspace memory continuity is verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [],
                "uncovered_modules": [
                    {
                        "module_id": "memory_runtime_simulation",
                        "reason": "The simulation verifies runtime memory behavior, not specialist execution.",
                    }
                ],
                "workflow_level_contract": {
                    "L": "Use one serial governed lane.",
                    "XL": "Use bounded waves when the approved organization needs them.",
                },
            }
        },
        ensure_ascii=False,
    )


def memory_benchmarks_enabled(env: Mapping[str, str] | None = None) -> bool:
    values = os.environ if env is None else env
    return str(values.get(RUN_MEMORY_BENCHMARKS_ENV, "")).strip() == "1"


def require_memory_benchmarks_enabled(env: Mapping[str, str] | None = None) -> None:
    if not memory_benchmarks_enabled(env):
        raise unittest.SkipTest(f"set {RUN_MEMORY_BENCHMARKS_ENV}=1 to run extended memory benchmark matrix")


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


def _is_wsl_bash_path(path: str) -> bool:
    normalized = path.replace("/", "\\").lower()
    return normalized.endswith("\\windows\\system32\\bash.exe") or normalized.endswith(
        "\\appdata\\local\\microsoft\\windowsapps\\bash.exe"
    )


def resolve_bash() -> str | None:
    candidates: list[str] = []
    first = shutil.which("bash")
    if first:
        candidates.append(first)
    if os.name == "nt":
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            for leaf in ("bash.exe", "bash"):
                candidate = Path(entry) / leaf
                if candidate.exists():
                    candidates.append(str(candidate))

    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        normalized = str(Path(candidate)).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(candidate)

    if os.name == "nt":
        for candidate in unique:
            if not _is_wsl_bash_path(candidate):
                return candidate
    return unique[0] if unique else None


def _run_path_tool(tool_name: str, flag: str, path: Path) -> str | None:
    tool = shutil.which(tool_name)
    if not tool:
        return None
    try:
        converted = subprocess.run(
            [tool, flag, str(path.resolve())],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    value = converted.stdout.strip()
    return value or None


def _bash_looks_like_wsl(bash: str | None = None) -> bool:
    bash = bash or resolve_bash()
    if not bash:
        return False
    return _is_wsl_bash_path(bash)


def _to_bash_path(path: Path, bash: str | None = None) -> str:
    resolved_path = path.resolve()
    resolved = str(resolved_path).replace("\\", "/")
    if len(resolved) >= 3 and resolved[1:3] == ":/":
        if not _bash_looks_like_wsl(bash):
            if "'" in str(resolved_path):
                return str(resolved_path)
            converted = _run_path_tool("cygpath", "-u", resolved_path) or _run_path_tool("wslpath", "-u", resolved_path)
            if converted:
                return converted
        return f"/mnt/{resolved[0].lower()}/{resolved[3:]}"
    return resolved


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_codex_test_prereqs() -> str:
    if resolve_powershell() is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")
    bash = resolve_bash()
    if bash is None:
        raise unittest.SkipTest("bash executable not available in PATH")
    return bash


def install_codex(target_root: Path, *, env: dict[str, str]) -> None:
    bash = require_codex_test_prereqs()
    skills_dir = target_root / "skills"
    command = [
        bash,
        str(INSTALL_SCRIPT),
        "--skills-dir",
        _to_bash_path(skills_dir, bash),
    ]
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
        timeout=INSTALL_TIMEOUT_SECONDS,
    )


def run_installed_runtime(
    installed_root: Path,
    *,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    workspace_root: Path | None = None,
    host_id: str = "codex",
    complete_agent_handoff: bool = True,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-codex-memory-sim-{host_id}-{uuid.uuid4().hex[:8]}"
    host_decision_json = _all_uncovered_host_decision_json()
    workspace_root_argument = (
        f"-WorkspaceRoot {_ps_single_quote(str(workspace_root))} "
        if workspace_root is not None
        else ""
    )
    effective_env = dict(env)
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_single_quote(str(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1'))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(run_id)} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
            f"{workspace_root_argument}"
            f"-HostDecisionJson {_ps_single_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=effective_env,
        check=True,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "installed invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    payload = json.loads(stdout)
    if not complete_agent_handoff:
        return payload
    return complete_module_execution(
        installed_root,
        task=task,
        artifact_root=artifact_root,
        env=effective_env,
        payload=payload,
        workspace_root=workspace_root,
    )


def complete_module_execution(
    installed_root: Path,
    *,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    payload: dict[str, object],
    workspace_root: Path | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    summary = payload["summary"]
    handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
    module_execution_path = Path(handoff["module_execution_path"])
    if module_execution_path.exists():
        raise AssertionError("plan_execute must leave module-execution.json for the Agent")
    result_contract = handoff["result_contract"]
    module_execution = json.loads(json.dumps(result_contract["submission_template"]))
    for unit in module_execution["units"]:
        unit["state"] = "completed"
        unit["result_summary"] = "The Agent completed the approved module work."
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

    run_id = str(payload["run_id"])
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
            f"$result = & {_ps_single_quote(str(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1'))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(run_id)} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
            f"{workspace_root_argument}"
            "-RequestedStageStop phase_cleanup "
            f"-ModuleExecutionJsonFile {_ps_single_quote(str(module_execution_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    return json.loads(completed.stdout.strip())


def run_repo_governed_runtime(
    task: str,
    artifact_root: Path,
    env: dict[str, str] | None = None,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-codex-shared-memory-" + uuid.uuid4().hex[:10]
    host_decision_json = _all_uncovered_host_decision_json()
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
            f"$result = & {_ps_single_quote(str(script_path))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(run_id)} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
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
        timeout=RUNTIME_INVOCATION_TIMEOUT_SECONDS,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    payload = json.loads(stdout)
    return complete_module_execution(
        REPO_ROOT,
        task=task,
        artifact_root=artifact_root,
        env=effective_env,
        payload=payload,
        workspace_root=workspace_root,
    )


def selected_capsule_text(context_pack: dict[str, object] | None) -> str:
    if not context_pack:
        return ""

    parts: list[str] = []
    for capsule in context_pack.get("selected_capsules") or []:
        parts.append(str(capsule.get("title") or ""))
        parts.extend(str(line) for line in capsule.get("summary_lines") or [])
    return "\n".join(part for part in parts if part).lower()


def extract_memory_metrics(payload: dict[str, object]) -> dict[str, object]:
    summary = payload["summary"]
    artifacts = summary["artifacts"]
    report_path = artifacts["memory_activation_report"]
    if not report_path:
        raise AssertionError(
            {
                "message": "memory benchmark payload returned before memory activation report was emitted",
                "terminal_stage": summary.get("terminal_stage"),
                "executed_stage_order": summary.get("executed_stage_order"),
                "host_user_briefing": payload.get("host_user_briefing"),
            }
        )

    report = load_json(report_path)
    stage_by_name = {stage["stage"]: stage for stage in report["stages"]}
    requirement_context = stage_by_name["requirement_doc"]["context_injection"]
    plan_context = stage_by_name["xl_plan"]["context_injection"]
    execute_context = stage_by_name["plan_execute"]["context_injection"]
    backend_hits = [
        {
            "stage": stage["stage"],
            "owner": action["owner"],
            "status": action["status"],
            "item_count": int(action.get("item_count") or 0),
        }
        for stage in report["stages"]
        for action in stage.get("read_actions", [])
        if str(action.get("owner")) in {"Serena", "Cognee", "ruflo"}
        and str(action.get("status")) == "backend_read"
        and int(action.get("item_count") or 0) > 0
    ]

    return {
        "report": report,
        "stage_by_name": stage_by_name,
        "requirement_context": requirement_context,
        "plan_context": plan_context,
        "execute_context": execute_context,
        "selected_text": "\n".join(
            [
                selected_capsule_text(requirement_context),
                selected_capsule_text(plan_context),
                selected_capsule_text(execute_context),
            ]
        ).lower(),
        "backend_hit_count": len(backend_hits),
        "backend_hits": backend_hits,
        "requirement_text": Path(payload["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower(),
        "plan_text": Path(payload["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower(),
    }


class CodexMemoryUserSimulationTests(unittest.TestCase):
    def _install_codex_context(self, root: Path, name: str) -> tuple[Path, Path, dict[str, str]]:
        target_root = root / name
        target_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["CODEX_HOME"] = str(target_root)
        install_codex(target_root, env=env)

        installed_root = target_root / "skills" / "vibe"
        self.assertTrue(installed_root.exists())
        return target_root, installed_root, env

    def _runtime_env(
        self,
        *,
        base_env: dict[str, str],
        target_root: Path,
        project_key: str,
        backend_root: Path | None = None,
    ) -> dict[str, str]:
        return {
            **base_env,
            "VCO_HOST_ID": "codex",
            "SERENA_PROJECT_KEY": project_key,
            "VIBE_MEMORY_BACKEND_ROOT": str(backend_root or (target_root / ".vibeskills" / "memory-backend")),
        }

    def _evaluate_installed_case(
        self,
        *,
        installed_root: Path,
        target_root: Path,
        base_env: dict[str, str],
        project_key: str,
        artifact_prefix: str,
        seed_tasks: list[str],
        follow_up_task: str,
        filler_tasks: list[str] | None = None,
        backend_root: Path | None = None,
    ) -> dict[str, object]:
        runtime_env = self._runtime_env(
            base_env=base_env,
            target_root=target_root,
            project_key=project_key,
            backend_root=backend_root,
        )
        workspace_root = target_root / "workspaces" / artifact_prefix

        for index, task in enumerate(seed_tasks):
            run_installed_runtime(
                installed_root,
                task=task,
                artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-seed-{index}",
                env=runtime_env,
                workspace_root=workspace_root,
            )
        for index, task in enumerate(filler_tasks or []):
            run_installed_runtime(
                installed_root,
                task=task,
                artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-filler-{index}",
                env=runtime_env,
                workspace_root=workspace_root,
            )

        payload = run_installed_runtime(
            installed_root,
            task=follow_up_task,
            artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-follow-up",
            env=runtime_env,
            workspace_root=workspace_root,
        )
        metrics = extract_memory_metrics(payload)
        metrics["payload"] = payload
        return metrics

    def test_install_codex_skips_cleanly_when_bash_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            with mock.patch("shutil.which", return_value=None), mock.patch("subprocess.run") as run_mock:
                with self.assertRaises(unittest.SkipTest):
                    install_codex(Path(tempdir), env=os.environ.copy())
                run_mock.assert_not_called()

    def test_install_codex_applies_timeout_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with mock.patch(
                f"{__name__}.require_codex_test_prereqs",
                return_value=r"C:\Program Files\Git\bin\bash.exe",
            ), mock.patch(f"{__name__}._to_bash_path", return_value="/tmp/codex-root"), mock.patch(
                "subprocess.run",
                return_value=completed,
            ) as run_mock:
                install_codex(target_root, env=os.environ.copy())

            self.assertEqual(INSTALL_TIMEOUT_SECONDS, run_mock.call_args.kwargs["timeout"])

    def test_quantitative_memory_benchmarks_are_opt_in(self) -> None:
        self.assertFalse(memory_benchmarks_enabled({}))
        with self.assertRaises(unittest.SkipTest):
            require_memory_benchmarks_enabled({})

        self.assertTrue(memory_benchmarks_enabled({RUN_MEMORY_BENCHMARKS_ENV: "1"}))
        require_memory_benchmarks_enabled({RUN_MEMORY_BENCHMARKS_ENV: "1"})

    def test_installed_runtime_helper_escapes_single_quotes_in_task_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-user-sim")
            runtime_env = self._runtime_env(
                base_env=base_env,
                target_root=target_root,
                project_key="pytest-codex-quoted-task",
            )

            payload = run_installed_runtime(
                installed_root,
                task="XL review planner's quartz-scheduler continuity before the next implementation step. $vibe",
                artifact_root=target_root / ".vibeskills" / "quote's-follow-up",
                env=runtime_env,
            )

            self.assertIn("summary", payload)
            self.assertTrue(
                Path(payload["summary"]["artifacts"]["requirement_doc"]).exists()
            )

    def test_codex_user_simulation_prefers_relevant_memory_and_keeps_injection_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-user-sim")
            runtime_env = {
                **base_env,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-codex-user-sim",
                "VIBE_MEMORY_BACKEND_ROOT": str(target_root / ".vibeskills" / "memory-backend"),
            }
            workspace_root = target_root / "workspaces" / "memory-sim"

            run_installed_runtime(
                installed_root,
                task="XL approved decision: keep quartz-scheduler runtime continuity and graph relationship between quartz-scheduler and planner. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-relevant-seed",
                env=runtime_env,
                workspace_root=workspace_root,
            )
            run_installed_runtime(
                installed_root,
                task="XL approved decision: retain billing-export continuity and graph relationship between billing-export and audit-ledger. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-irrelevant-seed",
                env=runtime_env,
                workspace_root=workspace_root,
            )
            follow_up = run_installed_runtime(
                installed_root,
                task="XL follow-up quartz-scheduler continuity review with planner dependency recall before the next implementation step. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-follow-up",
                env=runtime_env,
                workspace_root=workspace_root,
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            stage_by_name = {stage["stage"]: stage for stage in report["stages"]}
            requirement_stage = stage_by_name["requirement_doc"]
            requirement_context = requirement_stage["context_injection"]
            execute_context = stage_by_name["plan_execute"]["context_injection"]

            selected_text = "\n".join(
                "\n".join(
                    [
                        str(capsule.get("title") or ""),
                        *[str(line) for line in capsule.get("summary_lines") or []],
                    ]
                )
                for capsule in requirement_context["selected_capsules"]
            ).lower()
            referenced_payloads: set[str] = set()
            for capsule in requirement_context["selected_capsules"]:
                expansion_ref = str(capsule.get("expansion_ref") or "")
                if "#" in expansion_ref:
                    referenced_payloads.add(expansion_ref.split("#", 1)[0])
            total_candidates = sum(
                int(load_json(path).get("capsule_count") or 0)
                for path in referenced_payloads
            )

            self.assertIn("quartz-scheduler", selected_text)
            self.assertNotIn("billing-export", selected_text)
            self.assertEqual("decision_focused", requirement_context["disclosure_level"])
            self.assertEqual("execution_relevant", execute_context["disclosure_level"])
            self.assertLessEqual(
                len(requirement_context["selected_capsules"]),
                int(requirement_context["budget"]["top_k"]),
            )
            self.assertGreaterEqual(
                total_candidates,
                len(requirement_context["selected_capsules"]),
            )

            requirement_text = Path(follow_up["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower()
            plan_text = Path(follow_up["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower()
            requirement_receipt = load_json(follow_up["summary"]["artifacts"]["requirement_receipt"])
            plan_receipt = load_json(follow_up["summary"]["artifacts"]["execution_plan_receipt"])
            self.assertNotIn("## memory context", requirement_text)
            self.assertNotIn("## memory context", plan_text)
            self.assertGreaterEqual(int(requirement_receipt["memory_capsule_count"]), 1)
            self.assertTrue(bool(requirement_receipt["memory_context_path"]))
            self.assertGreaterEqual(int(plan_receipt["plan_memory_capsule_count"]), 1)
            self.assertTrue(bool(plan_receipt["plan_memory_context_path"]))

    def test_workspace_memory_is_shared_between_codex_and_claude_code_in_same_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_env = {
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "backends"),
                "SERENA_PROJECT_KEY": "pytest-shared-workspace-hosts",
            }
            shared_workspace_root = temp_root / "shared-workspace"

            run_repo_governed_runtime(
                "XL approved decision: keep atlas-cache runtime continuity and graph relationship between atlas-cache and planner. $vibe",
                artifact_root=temp_root / "codex-seed",
                env={**shared_env, "VCO_HOST_ID": "codex"},
                workspace_root=shared_workspace_root,
            )
            follow_up = run_repo_governed_runtime(
                "XL follow-up atlas-cache continuity review with planner dependency recall before the next step. $vibe",
                artifact_root=temp_root / "claude-follow-up",
                env={**shared_env, "VCO_HOST_ID": "claude-code"},
                workspace_root=shared_workspace_root,
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            read_actions = [
                action
                for stage in report["stages"]
                for action in stage.get("read_actions", [])
            ]

            self.assertTrue(
                any(
                    str(action.get("status")) == "backend_read" and int(action.get("item_count") or 0) > 0
                    for action in read_actions
                )
            )

            requirement_text = Path(follow_up["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower()
            plan_text = Path(follow_up["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower()
            self.assertIn("atlas-cache", requirement_text)
            self.assertIn("atlas-cache", plan_text)

    def test_workspace_memory_does_not_bleed_between_distinct_codex_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_backend_root = temp_root / "shared-backend-root"

            target_a, installed_a, env_a = self._install_codex_context(temp_root, "codex-workspace-a")
            target_b, installed_b, env_b = self._install_codex_context(temp_root, "codex-workspace-b")
            workspace_root_a = target_a / "workspace"
            workspace_root_b = target_b / "workspace"

            runtime_env_a = {
                **env_a,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-workspace-isolation",
                "VIBE_MEMORY_BACKEND_ROOT": str(shared_backend_root),
            }
            runtime_env_b = {
                **env_b,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-workspace-isolation",
                "VIBE_MEMORY_BACKEND_ROOT": str(shared_backend_root),
            }

            run_installed_runtime(
                installed_a,
                task="XL approved decision: keep orion-rewrite runtime continuity and graph relationship between orion-rewrite and reviewer. $vibe",
                artifact_root=target_a / ".vibeskills" / "workspace-a-seed",
                env=runtime_env_a,
                workspace_root=workspace_root_a,
            )
            follow_up = run_installed_runtime(
                installed_b,
                task="XL follow-up orion-rewrite continuity review with reviewer dependency recall before the next implementation step. $vibe",
                artifact_root=target_b / ".vibeskills" / "workspace-b-follow-up",
                env=runtime_env_b,
                workspace_root=workspace_root_b,
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            read_actions = [
                action
                for stage in report["stages"]
                for action in stage.get("read_actions", [])
            ]

            self.assertFalse(
                any(
                    str(action.get("status")) == "backend_read" and int(action.get("item_count") or 0) > 0
                    for action in read_actions
                )
            )
            self.assertTrue(any(str(action.get("status")) == "backend_read_empty" for action in read_actions))

    def test_quantitative_related_followup_hit_rate_meets_threshold(self) -> None:
        require_memory_benchmarks_enabled()
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-hit-rate")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
                f"XL approved decision: retain {IRRELEVANT_TOPIC} continuity and graph relationship between {IRRELEVANT_TOPIC} and {IRRELEVANT_DEPENDENCY}. $vibe",
            ]
            follow_up_tasks = [
                f"XL follow-up {RELEVANT_TOPIC} continuity review with {RELEVANT_DEPENDENCY} dependency recall before the next implementation step. $vibe",
                f"XL prepare {RELEVANT_TOPIC} execution plan using {RELEVANT_DEPENDENCY} continuity evidence before coding. $vibe",
                f"XL continue {RELEVANT_TOPIC} rollout planning with {RELEVANT_DEPENDENCY} linkage and prior continuity evidence before coding. $vibe",
                f"XL debug {RELEVANT_TOPIC} next step while preserving {RELEVANT_DEPENDENCY} continuity and prior relationship context. $vibe",
            ]

            hits = 0
            irrelevant_bleeds = 0
            for index, task in enumerate(follow_up_tasks):
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-hit-rate-{index}",
                    artifact_prefix=f"codex-hit-rate-{index}",
                    seed_tasks=seed_tasks,
                    follow_up_task=task,
                )
                if RELEVANT_TOPIC in str(metrics["selected_text"]) and int(metrics["backend_hit_count"]) >= 2:
                    hits += 1
                if IRRELEVANT_TOPIC in str(metrics["selected_text"]):
                    irrelevant_bleeds += 1

            hit_rate = hits / len(follow_up_tasks)
            bleed_rate = irrelevant_bleeds / len(follow_up_tasks)
            self.assertGreaterEqual(hit_rate, 1.0, {"hit_rate": hit_rate, "hits": hits})
            self.assertEqual(0.0, bleed_rate, {"bleed_rate": bleed_rate, "irrelevant_bleeds": irrelevant_bleeds})

    def test_quantitative_irrelevant_followup_false_recall_rate_stays_zero(self) -> None:
        require_memory_benchmarks_enabled()
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-false-recall")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
            ]
            unrelated_follow_ups = [
                "Prepare nebularender release notes and quartzcatalog acceptance criteria without touching other domains. $vibe",
                "Draft harborinvoice rollout notes and lanternledger acceptance criteria without recalling prior runtime continuity. $vibe",
                "Write willowqueue documentation and emberbatch success checks with no dependency recall. $vibe",
                "Plan skylinemeter cleanup guidance and riveraudit checklists without revisiting old execution history. $vibe",
            ]

            false_recalls = 0
            for index, task in enumerate(unrelated_follow_ups):
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-false-recall-{index}",
                    artifact_prefix=f"codex-false-recall-{index}",
                    seed_tasks=seed_tasks,
                    follow_up_task=task,
                )
                if int(metrics["backend_hit_count"]) > 0 or int(metrics["plan_context"]["capsule_count"]) > 0:
                    false_recalls += 1

            false_recall_rate = false_recalls / len(unrelated_follow_ups)
            self.assertEqual(
                0.0,
                false_recall_rate,
                {"false_recall_rate": false_recall_rate, "false_recalls": false_recalls},
            )

    def test_quantitative_recall_survives_intervening_turn_noise(self) -> None:
        require_memory_benchmarks_enabled()
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-decay")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
            ]
            filler_template = (
                "XL approved decision: retain {topic} continuity and graph relationship between {topic} and {dependency}. $vibe"
            )
            filler_pairs = [
                ("nebula-cache", "audit-anchor"),
                ("signal-router", "release-anchor"),
                ("harbor-metrics", "batch-window"),
            ]

            retained_hits = 0
            depths = [0, 1, 3]
            for depth in depths:
                filler_tasks = [
                    filler_template.format(topic=topic, dependency=dependency)
                    for topic, dependency in filler_pairs[:depth]
                ]
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-decay-{depth}",
                    artifact_prefix=f"codex-decay-{depth}",
                    seed_tasks=seed_tasks,
                    follow_up_task=(
                        f"XL follow-up {RELEVANT_TOPIC} continuity review with {RELEVANT_DEPENDENCY} dependency recall "
                        "before the next implementation step. $vibe"
                    ),
                    filler_tasks=filler_tasks,
                )
                if RELEVANT_TOPIC in str(metrics["selected_text"]) and int(metrics["backend_hit_count"]) >= 2:
                    retained_hits += 1

            retention_rate = retained_hits / len(depths)
            self.assertEqual(1.0, retention_rate, {"retention_rate": retention_rate, "retained_hits": retained_hits})

    def test_quantitative_cross_workspace_leak_rate_stays_zero(self) -> None:
        require_memory_benchmarks_enabled()
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_backend_root = temp_root / "shared-backend-root"

            target_a, installed_a, env_a = self._install_codex_context(temp_root, "codex-bench-workspace-a")
            target_b, installed_b, env_b = self._install_codex_context(temp_root, "codex-bench-workspace-b")

            topic_pairs = [
                ("orion-rewrite", "reviewer"),
                ("helix-cache", "planner"),
                ("signal-router", "release-anchor"),
            ]

            leaks = 0
            for index, (topic, dependency) in enumerate(topic_pairs):
                metrics_a = self._runtime_env(
                    base_env=env_a,
                    target_root=target_a,
                    project_key=f"pytest-codex-leak-{index}",
                    backend_root=shared_backend_root,
                )
                metrics_b = self._runtime_env(
                    base_env=env_b,
                    target_root=target_b,
                    project_key=f"pytest-codex-leak-{index}",
                    backend_root=shared_backend_root,
                )
                workspace_root_a = target_a / "workspaces" / f"leak-{index}"
                workspace_root_b = target_b / "workspaces" / f"leak-{index}"
                run_installed_runtime(
                    installed_a,
                    task=f"XL approved decision: keep {topic} runtime continuity and graph relationship between {topic} and {dependency}. $vibe",
                    artifact_root=target_a / ".vibeskills" / f"workspace-a-bench-seed-{index}",
                    env=metrics_a,
                    workspace_root=workspace_root_a,
                )
                payload = run_installed_runtime(
                    installed_b,
                    task=f"XL follow-up {topic} continuity review with {dependency} dependency recall before the next implementation step. $vibe",
                    artifact_root=target_b / ".vibeskills" / f"workspace-b-bench-follow-up-{index}",
                    env=metrics_b,
                    workspace_root=workspace_root_b,
                )
                metrics = extract_memory_metrics(payload)
                if int(metrics["backend_hit_count"]) > 0 or int(metrics["plan_context"]["capsule_count"]) > 0:
                    leaks += 1

            leak_rate = leaks / len(topic_pairs)
            self.assertEqual(0.0, leak_rate, {"leak_rate": leak_rate, "leaks": leaks})


if __name__ == "__main__":
    unittest.main()
