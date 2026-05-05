from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
SKILL_ROUTING_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeSkillRouting.Common.ps1"
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps_json(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class SkillExecutionLockContractTests(unittest.TestCase):
    def test_lock_projection_preserves_previous_selected_when_current_router_differs(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$previous = [pscustomobject]@{ "
            "  run_id = 'pytest-plan-run'; "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ "
            "      skill_id = 'scientific-reporting'; "
            "      task_slice = 'write paper'; "
            "      native_skill_entrypoint = 'C:/skills/scientific-reporting/SKILL.md'; "
            "      skill_md_path = 'C:/skills/scientific-reporting/SKILL.md'; "
            "      dispatch_phase = 'post_execution'; "
            "      write_scope = 'specialist:scientific-reporting'; "
            "      verification_expectation = 'report evidence' "
            "    }) "
            "  } "
            "}; "
            "$current = [pscustomobject]@{ "
            "  selected = @([pscustomobject]@{ "
            "    skill_id = 'latex-submission-pipeline'; "
            "    task_slice = 'compile pdf'; "
            "    native_skill_entrypoint = 'C:/skills/latex-submission-pipeline/SKILL.md'; "
            "    skill_md_path = 'C:/skills/latex-submission-pipeline/SKILL.md'; "
            "    dispatch_phase = 'post_execution'; "
            "    write_scope = 'specialist:latex-submission-pipeline'; "
            "    verification_expectation = 'build pdf' "
            "  }); "
            "  candidates = @(); rejected = @() "
            "}; "
            "$lock = New-VibeSkillExecutionLockProjection "
            "-PreviousRuntimeInputPacket $previous "
            "-CurrentSkillRouting $current "
            "-SourceRunId 'pytest-plan-run' "
            "-Source 'approved_plan_reentry'; "
            "$lock | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual("v1", payload["schema_version"])
        self.assertEqual("active", payload["state"])
        self.assertEqual("approved_plan_reentry", payload["source"])
        self.assertEqual("pytest-plan-run", payload["source_run_id"])
        self.assertIn("scientific-reporting", as_list(payload["locked_skill_ids"]))
        locked_dispatch = as_list(payload["locked_dispatch"])
        self.assertEqual("scientific-reporting", locked_dispatch[0]["skill_id"])
        self.assertEqual("inherited_not_currently_surfaced", locked_dispatch[0]["reconciliation_state"])
        self.assertTrue(payload["resolution_required"])

    def test_lock_projection_prefers_explicit_host_decision(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$previous = [pscustomobject]@{ "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ skill_id = 'scientific-reporting'; task_slice = 'prior plan' }) "
            "  } "
            "}; "
            "$current = [pscustomobject]@{ "
            "  selected = @([pscustomobject]@{ skill_id = 'latex-submission-pipeline'; task_slice = 'current pdf'; dispatch_phase = 'post_execution' }); "
            "  candidates = @([pscustomobject]@{ skill_id = 'designing-experiments'; task_slice = 'explicit design'; dispatch_phase = 'pre_execution' }); "
            "  rejected = @() "
            "}; "
            "$decision = [pscustomobject]@{ approved_skill_ids = @('designing-experiments') }; "
            "$lock = New-VibeSkillExecutionLockProjection "
            "-PreviousRuntimeInputPacket $previous "
            "-CurrentSkillRouting $current "
            "-HostSpecialistDispatchDecision $decision "
            "-SourceRunId 'pytest-plan-run' "
            "-Source 'approved_plan_reentry'; "
            "$lock | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["designing-experiments"], as_list(payload["locked_skill_ids"]))
        dispatch = as_list(payload["locked_dispatch"])[0]
        self.assertEqual("designing-experiments", dispatch["skill_id"])
        self.assertEqual("host_decision", dispatch["lock_source"])
        self.assertEqual("current_surfaced", dispatch["reconciliation_state"])

    def test_convert_lock_to_dispatch_preserves_dispatch_fields(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$lock = [pscustomobject]@{ "
            "  schema_version = 'v1'; state = 'active'; resolution_required = $true; "
            "  locked_dispatch = @([pscustomobject]@{ "
            "    skill_id = 'literature-review'; "
            "    task_slice = 'review authoritative literature'; "
            "    native_skill_entrypoint = 'C:/skills/literature-review/SKILL.md'; "
            "    skill_md_path = 'C:/skills/literature-review/SKILL.md'; "
            "    dispatch_phase = 'pre_execution'; "
            "    parallelizable_in_root_xl = $true; "
            "    write_scope = 'specialist:literature-review'; "
            "    verification_expectation = 'citation notes'; "
            "    lock_source = 'previous_skill_routing_selected' "
            "  }) "
            "}; "
            "$dispatch = Convert-VibeSkillExecutionLockToDispatch -SkillExecutionLock $lock; "
            "[pscustomobject]@{ dispatch = $dispatch } | ConvertTo-Json -Depth 20 "
            "}"
        )

        dispatch = as_list(payload["dispatch"])[0]
        self.assertEqual("literature-review", dispatch["skill_id"])
        self.assertEqual("pre_execution", dispatch["dispatch_phase"])
        self.assertEqual("specialist:literature-review", dispatch["write_scope"])
        self.assertEqual("citation notes", dispatch["verification_expectation"])
        self.assertTrue(dispatch["locked_for_execution"])

    def test_freeze_inherits_previous_plan_selection_into_execution_lock(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            prior_session = artifact_root / "outputs" / "runtime" / "vibe-sessions" / "pytest-plan-run"
            prior_session.mkdir(parents=True)
            (prior_session / "runtime-input-packet.json").write_text(
                json.dumps(
                    {
                        "run_id": "pytest-plan-run",
                        "requested_stage_stop": "xl_plan",
                        "skill_routing": {
                            "schema_version": "simplified_skill_routing_v1",
                            "selected": [
                                {
                                    "skill_id": "scientific-reporting",
                                    "task_slice": "write a scientific report",
                                    "native_skill_entrypoint": "C:/skills/scientific-reporting/SKILL.md",
                                    "skill_md_path": "C:/skills/scientific-reporting/SKILL.md",
                                    "dispatch_phase": "post_execution",
                                    "write_scope": "specialist:scientific-reporting",
                                    "verification_expectation": "report evidence",
                                }
                            ],
                            "candidates": [],
                            "rejected": [],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            host_decision = {
                "decision_kind": "approval_response",
                "decision_action": "approve_plan",
                "approval_decision": "approve",
                "continuation_context": {
                    "structured_bounded_reentry": True,
                    "source_run_id": "pytest-plan-run",
                    "reentry_action": "approve_plan",
                    "prior_task_type": "research",
                    "control_only_prompt": True,
                },
            }
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(FREEZE_SCRIPT),
                    "-Task",
                    "Continue approved plan and compile the LaTeX paper.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-execute-run",
                    "-ArtifactRoot",
                    str(artifact_root),
                    "-HostDecisionJson",
                    json.dumps(host_decision),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            self.assertIn("packet_path", completed.stdout)
            packet_path = next(
                (artifact_root / "outputs" / "runtime" / "vibe-sessions" / "pytest-execute-run").rglob(
                    "runtime-input-packet.json"
                )
            )
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        lock = packet["skill_execution_lock"]
        self.assertEqual("active", lock["state"])
        self.assertIn("scientific-reporting", as_list(lock["locked_skill_ids"]))
        self.assertTrue(lock["resolution_required"])

    def test_lock_dispatch_is_preferred_over_current_router_selection_projection(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$runtimePacket = [pscustomobject]@{ "
            "  skill_execution_lock = [pscustomobject]@{ "
            "    schema_version = 'v1'; state = 'active'; resolution_required = $true; "
            "    locked_dispatch = @([pscustomobject]@{ "
            "      skill_id = 'scientific-reporting'; task_slice = 'locked report'; dispatch_phase = 'post_execution'; "
            "      write_scope = 'specialist:scientific-reporting'; verification_expectation = 'report evidence' "
            "    }) "
            "  }; "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ skill_id = 'latex-submission-pipeline'; task_slice = 'current pdf'; dispatch_phase = 'post_execution' }) "
            "  } "
            "}; "
            "$lockDispatch = Convert-VibeSkillExecutionLockToDispatch -SkillExecutionLock $runtimePacket.skill_execution_lock; "
            "$currentDispatch = Convert-VibeSkillRoutingSelectedToDispatch -RuntimeInputPacket $runtimePacket -SkillRouting $runtimePacket.skill_routing; "
            "[pscustomobject]@{ lock_dispatch = $lockDispatch; current_dispatch = $currentDispatch } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["scientific-reporting"], [item["skill_id"] for item in as_list(payload["lock_dispatch"])])
        self.assertEqual(["latex-submission-pipeline"], [item["skill_id"] for item in as_list(payload["current_dispatch"])])
