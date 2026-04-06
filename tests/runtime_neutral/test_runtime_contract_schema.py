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
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
EXECUTION_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
SPECIALIST_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."


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


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps_json(body: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", body],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def run_runtime(artifact_root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-contract-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{RUNTIME_ENTRY}' "
                f"-Task '{SPECIALIST_TASK}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, **(extra_env or {})},
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class RuntimeContractSchemaTests(unittest.TestCase):
    def test_workspace_artifact_projection_defaults_to_repo_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_root_text = str(workspace_root.resolve())

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                "$result = New-VibeWorkspaceArtifactProjection "
                f"-RepoRoot {_ps_single_quote(workspace_root_text)} "
                "-ArtifactRoot ''; "
                "$result | ConvertTo-Json -Depth 10 }"
            )

        self.assertEqual(workspace_root_text, payload["workspace_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills", payload["workspace_sidecar_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills", payload["artifact_root"])
        self.assertEqual("workspace_sidecar_default", payload["artifact_root_source"])
        self.assertTrue(payload["default_workspace_sidecar_artifact_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills/project.json", payload["project_descriptor_path"])

    def test_session_root_initialization_persists_host_sidecar_root_from_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            host_root = Path(tempdir) / "cursor-home"
            workspace_root.mkdir(parents=True, exist_ok=True)
            host_root.mkdir(parents=True, exist_ok=True)
            descriptor_path = workspace_root / ".vibeskills" / "project.json"

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                "$runtime = [pscustomobject]@{ "
                "host_settings = [pscustomobject]@{ "
                f"target_root = {_ps_single_quote(str(host_root.resolve()))} "
                "} "
                "}; "
                "$sessionRoot = Ensure-VibeSessionRoot "
                f"-RepoRoot {_ps_single_quote(str(workspace_root.resolve()))} "
                "-RunId 'run-session-root-host-sidecar' "
                "-ArtifactRoot '' "
                "-Runtime $runtime; "
                f"$descriptor = Get-Content -LiteralPath {_ps_single_quote(str(descriptor_path.resolve()))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                "[pscustomobject]@{ "
                "session_root = $sessionRoot; "
                "host_sidecar_root = $descriptor.host_sidecar_root "
                "} | ConvertTo-Json -Depth 10 }"
            )

        self.assertEqual(str((host_root / ".vibeskills").resolve()), payload["host_sidecar_root"])

    def test_identity_projection_preserves_requested_and_effective_ids(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
            "$adapter = [pscustomobject]@{ "
            "requested_id = 'cursor'; "
            "id = 'windsurf'; "
            "status = 'preview'; "
            "install_mode = 'scaffold'; "
            "check_mode = 'audit'; "
            "bootstrap_mode = 'bounded' "
            "}; "
            "$result = Get-VibeHostAdapterIdentityProjection "
            "-HostAdapter $adapter "
            "-RequestedPropertyName 'requested_id' "
            "-EffectivePropertyName 'id' "
            "-FallbackHostId 'codex'; "
            "$result | ConvertTo-Json -Depth 10 }"
        )

        self.assertEqual("cursor", payload["requested_host_id"])
        self.assertEqual("windsurf", payload["effective_host_id"])

    def test_runtime_projection_maps_status_modes_closure_and_host_settings(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
            "$runtime = [pscustomobject]@{ "
            "host_adapter = [pscustomobject]@{ "
            "requested_id = 'openclaw'; "
            "id = 'openclaw'; "
            "status = 'preview'; "
            "install_mode = 'scaffold'; "
            "check_mode = 'audit'; "
            "bootstrap_mode = 'bounded' "
            "}; "
            "host_closure = [pscustomobject]@{ path = '/tmp/host-closure.json' }; "
            "host_settings = [pscustomobject]@{ path = '/tmp/host-settings.json' } "
            "}; "
            "$result = New-VibeRuntimeHostAdapterProjection "
            "-Runtime $runtime "
            "-FallbackHostId 'codex' "
            "-TargetRoot '/tmp/openclaw-home'; "
            "$result | ConvertTo-Json -Depth 10 }"
        )

        self.assertEqual("openclaw", payload["requested_host_id"])
        self.assertEqual("openclaw", payload["effective_host_id"])
        self.assertEqual("preview", payload["status"])
        self.assertEqual("scaffold", payload["install_mode"])
        self.assertEqual("audit", payload["check_mode"])
        self.assertEqual("bounded", payload["bootstrap_mode"])
        self.assertEqual("/tmp/openclaw-home", payload["target_root"])
        self.assertEqual("/tmp/host-closure.json", payload["closure_path"])
        self.assertEqual("/tmp/host-settings.json", payload["host_settings_path"])

    def test_runtime_packet_alignment_helper_reads_frozen_projection(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "host_adapter = [pscustomobject]@{ requested_host_id = 'openclaw'; effective_host_id = 'windsurf' } "
            "}; "
            "$result = Get-VibeRuntimePacketHostAdapterAlignment -RuntimeInputPacket $packet; "
            "$result | ConvertTo-Json -Depth 10 }"
        )

        self.assertEqual("openclaw", payload["requested_host_id"])
        self.assertEqual("windsurf", payload["effective_host_id"])

    def test_bridge_resolution_can_use_host_settings_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            launcher = temp_path / "openclaw-wrapper.sh"
            launcher.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                "$adapter = [pscustomobject]@{ id = 'openclaw'; bridge_executable_env = ''; bridge_command = '' }; "
                "$runtime = [pscustomobject]@{ "
                "host_settings = [pscustomobject]@{ "
                f"path = {_ps_single_quote(str(temp_path / '.vibeskills' / 'host-settings.json'))}; "
                "data = [pscustomobject]@{ "
                "specialist_wrapper = [pscustomobject]@{ "
                f"launcher_path = {_ps_single_quote(str(launcher))}; "
                "ready = $true "
                "} "
                "} "
                "} "
                "}; "
                "$result = Resolve-VibeBridgeExecutable -Adapter $adapter -Runtime $runtime; "
                "$result | ConvertTo-Json -Depth 10 }"
            )

        self.assertEqual(str(launcher), payload["command_path"])
        self.assertEqual("native_specialist_bridge_ready", payload["reason"])

    def test_hierarchy_projection_preserves_root_and_child_fields(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
            "$root = New-VibeHierarchyProjection "
            "-HierarchyState ([pscustomobject]@{ "
            "governance_scope = 'root'; "
            "root_run_id = 'root-1'; "
            "parent_run_id = $null; "
            "parent_unit_id = $null; "
            "inherited_requirement_doc_path = $null; "
            "inherited_execution_plan_path = $null "
            "}) "
            "-IncludeGovernanceScope; "
            "$child = New-VibeHierarchyProjection "
            "-HierarchyState ([pscustomobject]@{ "
            "governance_scope = 'child'; "
            "root_run_id = 'root-2'; "
            "parent_run_id = 'parent-2'; "
            "parent_unit_id = 'unit-2'; "
            "inherited_requirement_doc_path = '/tmp/req.md'; "
            "inherited_execution_plan_path = '/tmp/plan.md' "
            "}) "
            "-IncludeGovernanceScope; "
            "@($root, $child) | ConvertTo-Json -Depth 10 }"
        )

        self.assertEqual("root", payload[0]["governance_scope"])
        self.assertEqual("root-1", payload[0]["root_run_id"])
        self.assertIsNone(payload[0]["parent_run_id"])
        self.assertIsNone(payload[0]["parent_unit_id"])
        self.assertEqual("child", payload[1]["governance_scope"])
        self.assertEqual("root-2", payload[1]["root_run_id"])
        self.assertEqual("parent-2", payload[1]["parent_run_id"])
        self.assertEqual("unit-2", payload[1]["parent_unit_id"])
        self.assertEqual("/tmp/req.md", payload[1]["inherited_requirement_doc_path"])
        self.assertEqual("/tmp/plan.md", payload[1]["inherited_execution_plan_path"])

    def test_authority_projection_preserves_runtime_and_execution_contracts(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
            "$rootState = [pscustomobject]@{ "
            "allow_requirement_freeze = $true; "
            "allow_plan_freeze = $true; "
            "allow_global_dispatch = $true; "
            "allow_completion_claim = $true "
            "}; "
            "$childState = [pscustomobject]@{ "
            "allow_requirement_freeze = $false; "
            "allow_plan_freeze = $false; "
            "allow_global_dispatch = $false; "
            "allow_completion_claim = $false "
            "}; "
            "$payload = [pscustomobject]@{ "
            "root_capability = (New-VibeAuthorityCapabilityProjection -HierarchyState $rootState); "
            "root_runtime = (New-VibeRuntimePacketAuthorityFlagsProjection -HierarchyState $rootState -RuntimeEntry 'vibe' -ExplicitRuntimeSkill 'vibe' -RouterTruthLevel 'authoritative' -ShadowOnly $true -NonAuthoritative $false); "
            "root_execution = (New-VibeExecutionAuthorityProjection -HierarchyState $rootState); "
            "child_capability = (New-VibeAuthorityCapabilityProjection -HierarchyState $childState); "
            "child_execution = (New-VibeExecutionAuthorityProjection -HierarchyState $childState) "
            "}; "
            "$payload | ConvertTo-Json -Depth 10 }"
        )

        self.assertTrue(payload["root_capability"]["allow_requirement_freeze"])
        self.assertTrue(payload["root_capability"]["allow_plan_freeze"])
        self.assertTrue(payload["root_capability"]["allow_global_dispatch"])
        self.assertTrue(payload["root_capability"]["allow_completion_claim"])
        self.assertEqual("vibe", payload["root_runtime"]["runtime_entry"])
        self.assertEqual("vibe", payload["root_runtime"]["explicit_runtime_skill"])
        self.assertEqual("authoritative", payload["root_runtime"]["router_truth_level"])
        self.assertTrue(payload["root_runtime"]["shadow_only"])
        self.assertFalse(payload["root_runtime"]["non_authoritative"])
        self.assertTrue(payload["root_runtime"]["allow_completion_claim"])
        self.assertTrue(payload["root_execution"]["canonical_requirement_write_allowed"])
        self.assertTrue(payload["root_execution"]["canonical_plan_write_allowed"])
        self.assertTrue(payload["root_execution"]["global_dispatch_allowed"])
        self.assertTrue(payload["root_execution"]["completion_claim_allowed"])
        self.assertFalse(payload["child_capability"]["allow_requirement_freeze"])
        self.assertFalse(payload["child_capability"]["allow_plan_freeze"])
        self.assertFalse(payload["child_capability"]["allow_global_dispatch"])
        self.assertFalse(payload["child_capability"]["allow_completion_claim"])
        self.assertFalse(payload["child_execution"]["canonical_requirement_write_allowed"])
        self.assertFalse(payload["child_execution"]["canonical_plan_write_allowed"])
        self.assertFalse(payload["child_execution"]["global_dispatch_allowed"])
        self.assertFalse(payload["child_execution"]["completion_claim_allowed"])

    def test_runtime_input_packet_projection_preserves_route_dispatch_and_custom_admission_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_root_text = str(workspace_root.resolve())

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                "$hierarchyState = [pscustomobject]@{ governance_scope = 'child'; root_run_id = 'root-7'; parent_run_id = 'parent-7'; parent_unit_id = 'unit-7'; inherited_requirement_doc_path = '/tmp/req.md'; inherited_execution_plan_path = '/tmp/plan.md' }; "
                "$hierarchy = New-VibeHierarchyProjection -HierarchyState $hierarchyState -IncludeGovernanceScope; "
                "$authority = New-VibeRuntimePacketAuthorityFlagsProjection -HierarchyState $hierarchyState -RuntimeEntry 'vibe' -ExplicitRuntimeSkill 'vibe' -RouterTruthLevel 'shadow' -ShadowOnly $true -NonAuthoritative $false; "
                f"$storage = New-VibeWorkspaceArtifactProjection -RepoRoot {_ps_single_quote(workspace_root_text)} -ArtifactRoot ''; "
                "$route = [pscustomobject]@{ "
                "selected = [pscustomobject]@{ pack_id = 'runtime-governor'; skill = 'systematic-debugging' }; "
                "route_mode = 'confirm_required'; "
                "route_reason = 'fixture'; "
                "confidence = 0.75; "
                "truth_level = 'shadow'; "
                "degradation_state = 'none'; "
                "non_authoritative = $false; "
                "fallback_active = $false; "
                "hazard_alert_required = $true; "
                "unattended_override_applied = $false; "
                "custom_admission = [pscustomobject]@{ status = 'admitted'; target_root = '/tmp/custom'; admitted_candidates = @([pscustomobject]@{ skill_id = 'systematic-debugging' }, [pscustomobject]@{ skill_id = 'think-harder' }) } "
                "}; "
                "$runtime = [pscustomobject]@{ host_adapter = [pscustomobject]@{ requested_id = 'openclaw'; id = 'openclaw'; status = 'preview'; install_mode = 'scaffold'; check_mode = 'audit'; bootstrap_mode = 'bounded' }; host_closure = [pscustomobject]@{ path = '/tmp/closure.json' } }; "
                "$dispatch = [pscustomobject]@{ approved_dispatch = @([pscustomobject]@{ skill_id = 'systematic-debugging' }); local_specialist_suggestions = @([pscustomobject]@{ skill_id = 'think-harder' }); escalation_required = $true; escalation_status = 'pending_root_approval' }; "
                "$policy = [pscustomobject]@{ freeze_before_requirement_doc = $true; child_specialist_suggestion_contract = [pscustomobject]@{ approval_owner = 'root_vibe'; status = 'advisory_until_root_approval' } }; "
                "$packet = New-VibeRuntimeInputPacketProjection "
                "-RunId 'run-7' "
                "-Task 'debug task' "
                "-Mode 'interactive_governed' "
                "-InternalGrade 'XL' "
                "-HierarchyState $hierarchyState "
                "-HierarchyProjection $hierarchy "
                "-AuthorityFlagsProjection $authority "
                "-StorageProjection $storage "
                "-RouteResult $route "
                "-Runtime $runtime "
                "-TaskType 'debug' "
                "-RequestedSkill 'vibe' "
                "-RouterHostId 'openclaw' "
                "-RouterTargetRoot '/tmp/openclaw' "
                "-Unattended:$false "
                "-RouterScriptPath '/tmp/router.ps1' "
                "-RuntimeSelectedSkill 'vibe' "
                "-SpecialistRecommendations @([pscustomobject]@{ skill_id = 'systematic-debugging'; native_usage_required = $true }) "
                "-SpecialistDispatch $dispatch "
                "-OverlayDecisions @([pscustomobject]@{ name = 'danger'; decision = 'observe' }) "
                "-Policy $policy; "
                "$packet | ConvertTo-Json -Depth 20 }"
            )

        self.assertEqual("runtime_input_freeze", payload["stage"])
        self.assertEqual("run-7", payload["run_id"])
        self.assertEqual("child", payload["governance_scope"])
        self.assertEqual("systematic-debugging", payload["route_snapshot"]["selected_skill"])
        self.assertTrue(payload["route_snapshot"]["confirm_required"])
        self.assertEqual("admitted", payload["custom_admission"]["status"])
        self.assertEqual(2, payload["custom_admission"]["admitted_candidate_count"])
        self.assertEqual(["systematic-debugging"], payload["specialist_dispatch"]["approved_skill_ids"])
        self.assertEqual(["think-harder"], payload["specialist_dispatch"]["local_suggestion_skill_ids"])
        self.assertTrue(payload["specialist_dispatch"]["escalation_required"])
        self.assertEqual("vibe", payload["divergence_shadow"]["runtime_selected_skill"])
        self.assertTrue(payload["divergence_shadow"]["skill_mismatch"])
        self.assertEqual("openclaw", payload["host_adapter"]["requested_host_id"])
        self.assertEqual("openclaw", payload["host_adapter"]["effective_host_id"])
        self.assertEqual(workspace_root_text, payload["storage"]["workspace_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills", payload["storage"]["workspace_sidecar_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills", payload["storage"]["artifact_root"])
        self.assertEqual("workspace_sidecar_default", payload["storage"]["artifact_root_source"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills/project.json", payload["storage"]["project_descriptor_path"])
        self.assertTrue(payload["provenance"]["freeze_before_requirement_doc"])

    def test_runtime_summary_projection_preserves_public_contract_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            host_root = Path(tempdir) / "openclaw"
            root_path = Path(tempdir) / "root"
            workspace_root_text = str(workspace_root.resolve())
            host_root_text = str(host_root.resolve())
            root_path_text = str(root_path.resolve())

            payload = run_ps_json(
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                "$hierarchyState = [pscustomobject]@{ "
                "governance_scope = 'child'; "
                "root_run_id = 'root-9'; "
                "parent_run_id = 'parent-9'; "
                "parent_unit_id = 'unit-9'; "
                "inherited_requirement_doc_path = '/tmp/req.md'; "
                "inherited_execution_plan_path = '/tmp/plan.md' "
                "}; "
                "$artifacts = New-VibeRuntimeSummaryArtifactProjection "
                "-SkeletonReceiptPath '/tmp/skeleton.json' "
                "-RuntimeInputPacketPath '/tmp/runtime-input.json' "
                "-IntentContractPath '/tmp/intent.json' "
                "-RequirementDocPath '/tmp/req.md' "
                "-RequirementReceiptPath '/tmp/req-receipt.json' "
                "-ExecutionPlanPath '/tmp/plan.md' "
                "-ExecutionPlanReceiptPath '/tmp/plan-receipt.json' "
                "-ExecuteReceiptPath '/tmp/execute.json' "
                "-ExecutionManifestPath '/tmp/manifest.json' "
                "-ExecutionTopologyPath '/tmp/topology.json' "
                "-ExecutionProofManifestPath '/tmp/proof.json' "
                "-CleanupReceiptPath '/tmp/cleanup.json' "
                "-DeliveryAcceptanceReportPath '/tmp/delivery.json' "
                "-DeliveryAcceptanceMarkdownPath '/tmp/delivery.md' "
                "-MemoryActivationReportPath '/tmp/memory.json' "
                "-MemoryActivationMarkdownPath '/tmp/memory.md'; "
                "$relative = [pscustomobject]@{ "
                "skeleton_receipt = 'outputs/runtime/vibe-sessions/run/skeleton.json'; "
                "runtime_input_packet = 'outputs/runtime/vibe-sessions/run/runtime-input.json'; "
                "intent_contract = 'outputs/runtime/vibe-sessions/run/intent.json'; "
                "requirement_doc = 'docs/requirements/req.md'; "
                "requirement_receipt = 'outputs/runtime/vibe-sessions/run/req-receipt.json'; "
                "execution_plan = 'docs/plans/plan.md'; "
                "execution_plan_receipt = 'outputs/runtime/vibe-sessions/run/plan-receipt.json'; "
                "execute_receipt = 'outputs/runtime/vibe-sessions/run/execute.json'; "
                "execution_manifest = 'outputs/runtime/vibe-sessions/run/manifest.json'; "
                "execution_topology = 'outputs/runtime/vibe-sessions/run/topology.json'; "
                "execution_proof_manifest = 'outputs/runtime/vibe-sessions/run/proof.json'; "
                "cleanup_receipt = 'outputs/runtime/vibe-sessions/run/cleanup.json'; "
                "delivery_acceptance_report = 'outputs/runtime/vibe-sessions/run/delivery.json'; "
                "delivery_acceptance_markdown = 'outputs/runtime/vibe-sessions/run/delivery.md'; "
                "memory_activation_report = 'outputs/runtime/vibe-sessions/run/memory.json'; "
                "memory_activation_markdown = 'outputs/runtime/vibe-sessions/run/memory.md' "
                "}; "
                "$memory = [pscustomobject]@{ "
                "policy = [pscustomobject]@{ mode = 'shadow'; routing_contract = 'advisory_first_post_route_only' }; "
                "summary = [pscustomobject]@{ fallback_event_count = 2; artifact_count = 4; budget_guard_respected = $true } "
                "}; "
                "$delivery = [pscustomobject]@{ "
                "summary = [pscustomobject]@{ gate_result = 'PASS'; completion_language_allowed = $true; readiness_state = 'passing'; manual_review_layer_count = 0; failing_layer_count = 0 } "
                "}; "
                "$storage = [pscustomobject]@{ "
                f"workspace_root = {_ps_single_quote(workspace_root_text)}; "
                f"workspace_sidecar_root = {_ps_single_quote(workspace_root_text + '/.vibeskills')}; "
                f"project_descriptor_path = {_ps_single_quote(workspace_root_text + '/.vibeskills/project.json')}; "
                f"artifact_root = {_ps_single_quote(workspace_root_text + '/.vibeskills')}; "
                "artifact_root_source = 'workspace_sidecar_default'; "
                "default_workspace_sidecar_artifact_root = $true; "
                f"host_sidecar_root = {_ps_single_quote(host_root_text + '/.vibeskills')} "
                "}; "
                "$result = New-VibeRuntimeSummaryProjection "
                "-RunId 'run-9' "
                "-Mode 'interactive_governed' "
                "-Task 'task-9' "
                f"-ArtifactRoot {_ps_single_quote(root_path_text)} "
                f"-SessionRoot {_ps_single_quote(root_path_text + '/outputs/runtime/vibe-sessions/run-9')} "
                "-HierarchyState $hierarchyState "
                "-Artifacts $artifacts "
                "-RelativeArtifacts $relative "
                "-StorageProjection $storage "
                "-MemoryActivationReport $memory "
                "-DeliveryAcceptanceReport $delivery; "
                "$result | ConvertTo-Json -Depth 20 }"
            )

        self.assertEqual("run-9", payload["run_id"])
        self.assertEqual("child", payload["governance_scope"])
        self.assertEqual("interactive_governed", payload["mode"])
        self.assertEqual("task-9", payload["task"])
        self.assertEqual("outputs/runtime/vibe-sessions/run/skeleton.json", payload["artifacts_relative"]["skeleton_receipt"])
        self.assertEqual("/tmp/manifest.json", payload["artifacts"]["execution_manifest"])
        self.assertEqual("root-9", payload["hierarchy"]["root_run_id"])
        self.assertEqual("parent-9", payload["hierarchy"]["parent_run_id"])
        self.assertEqual("unit-9", payload["hierarchy"]["parent_unit_id"])
        self.assertEqual("/tmp/req.md", payload["hierarchy"]["inherited_requirement_doc_path"])
        self.assertEqual(
            [
                "skeleton_check",
                "deep_interview",
                "requirement_doc",
                "xl_plan",
                "plan_execute",
                "phase_cleanup",
            ],
            payload["stage_order"],
        )
        self.assertEqual("shadow", payload["memory_activation"]["policy_mode"])
        self.assertEqual(2, payload["memory_activation"]["fallback_event_count"])
        self.assertTrue(payload["memory_activation"]["budget_guard_respected"])
        self.assertEqual("PASS", payload["delivery_acceptance"]["gate_result"])
        self.assertTrue(payload["delivery_acceptance"]["completion_language_allowed"])
        self.assertEqual(workspace_root_text, payload["storage"]["workspace_root"])
        self.assertEqual(f"{workspace_root_text}/.vibeskills", payload["storage"]["workspace_sidecar_root"])
        self.assertEqual("workspace_sidecar_default", payload["storage"]["artifact_root_source"])
        self.assertTrue(payload["storage"]["default_workspace_sidecar_artifact_root"])

    def test_runtime_packet_storage_projection_tracks_workspace_sidecar_when_artifact_root_is_overridden(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                Path(tempdir),
                extra_env={"VCO_HOST_ID": "openclaw"},
            )
            runtime_input = load_json(payload["summary"]["artifacts"]["runtime_input_packet"])
            storage = runtime_input["storage"]

            self.assertEqual(str(REPO_ROOT.resolve()), storage["workspace_root"])
            self.assertEqual(str((REPO_ROOT / ".vibeskills").resolve()), storage["workspace_sidecar_root"])
            self.assertEqual(str(Path(tempdir).resolve()), storage["artifact_root"])
            self.assertEqual("explicit_override", storage["artifact_root_source"])
            self.assertFalse(storage["default_workspace_sidecar_artifact_root"])
            self.assertEqual(
                str((REPO_ROOT / ".vibeskills" / "project.json").resolve()),
                storage["project_descriptor_path"],
            )

    def test_runtime_packet_execution_manifest_and_specialist_accounting_stay_aligned(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                Path(tempdir),
                extra_env={"VCO_HOST_ID": "openclaw"},
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            runtime_host = runtime_input["host_adapter"]
            alignment = execution_manifest["route_runtime_alignment"]
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertEqual("openclaw", runtime_host["requested_host_id"])
            self.assertEqual("openclaw", runtime_host["effective_host_id"])
            self.assertEqual(runtime_host["requested_host_id"], alignment["requested_host_adapter_id"])
            self.assertEqual(runtime_host["effective_host_id"], alignment["effective_host_adapter_id"])
            self.assertEqual(runtime_host["requested_host_id"], specialist_accounting["requested_host_adapter_id"])
            self.assertEqual(runtime_host["effective_host_id"], specialist_accounting["effective_host_adapter_id"])

    def test_skill_promotion_contract_fields_are_present_in_runtime_and_execution_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                Path(tempdir),
                extra_env={"VCO_HOST_ID": "openclaw"},
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            dispatch = runtime_input["specialist_dispatch"]
            for field in (
                "matched_skill_ids",
                "surfaced_skill_ids",
                "blocked_skill_ids",
                "degraded_skill_ids",
                "ghost_match_skill_ids",
                "promotion_outcomes",
            ):
                with self.subTest(field=field):
                    self.assertIn(field, dispatch)

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertIn("promotion_funnel", specialist_accounting)
            for field in (
                "matched",
                "surfaced",
                "dispatched",
                "executed",
                "blocked_due_to_destructive",
                "degraded_due_to_missing_contract",
                "ghost_match",
            ):
                with self.subTest(field=field):
                    self.assertIn(field, specialist_accounting["promotion_funnel"])

    def test_runtime_packet_and_execution_manifest_share_hierarchy_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual(runtime_input["hierarchy"], execution_manifest["hierarchy"])
            self.assertEqual("root", runtime_input["hierarchy"]["governance_scope"])
            self.assertEqual(runtime_input["run_id"], runtime_input["hierarchy"]["root_run_id"])

    def test_runtime_packet_execution_manifest_and_execute_receipt_share_authority_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            execute_receipt = load_json(summary["artifacts"]["execute_receipt"])

            authority_flags = runtime_input["authority_flags"]
            authority = execution_manifest["authority"]

            self.assertEqual(
                authority_flags["allow_requirement_freeze"],
                authority["canonical_requirement_write_allowed"],
            )
            self.assertEqual(
                authority_flags["allow_plan_freeze"],
                authority["canonical_plan_write_allowed"],
            )
            self.assertEqual(
                authority_flags["allow_global_dispatch"],
                authority["global_dispatch_allowed"],
            )
            self.assertEqual(
                authority_flags["allow_completion_claim"],
                authority["completion_claim_allowed"],
            )
            self.assertEqual(
                authority["completion_claim_allowed"],
                execute_receipt["completion_claim_allowed"],
            )

    def test_runtime_payload_summary_matches_runtime_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary_from_payload = payload["summary"]
            summary_from_file = load_json(payload["summary_path"])

            self.assertEqual(summary_from_payload, summary_from_file)
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan", "plan_execute", "phase_cleanup"],
                summary_from_file["stage_order"],
            )
            self.assertEqual(
                summary_from_file["artifacts"]["memory_activation_report"],
                summary_from_payload["artifacts"]["memory_activation_report"],
            )
            self.assertEqual(
                summary_from_file["artifacts_relative"]["execution_manifest"],
                summary_from_payload["artifacts_relative"]["execution_manifest"],
            )

    def test_runtime_summary_blocks_align_with_hierarchy_and_report_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            memory_report = load_json(summary["artifacts"]["memory_activation_report"])
            delivery_report = load_json(summary["artifacts"]["delivery_acceptance_report"])

            self.assertEqual(
                runtime_input["hierarchy"]["root_run_id"],
                summary["hierarchy"]["root_run_id"],
            )
            self.assertEqual(
                runtime_input["hierarchy"]["parent_run_id"],
                summary["hierarchy"]["parent_run_id"],
            )
            self.assertEqual(
                runtime_input["hierarchy"]["parent_unit_id"],
                summary["hierarchy"]["parent_unit_id"],
            )
            self.assertEqual(
                memory_report["policy"]["mode"],
                summary["memory_activation"]["policy_mode"],
            )
            self.assertEqual(
                memory_report["policy"]["routing_contract"],
                summary["memory_activation"]["routing_contract"],
            )
            self.assertEqual(
                memory_report["summary"]["fallback_event_count"],
                summary["memory_activation"]["fallback_event_count"],
            )
            self.assertEqual(
                memory_report["summary"]["artifact_count"],
                summary["memory_activation"]["artifact_count"],
            )
            self.assertEqual(
                delivery_report["summary"]["gate_result"],
                summary["delivery_acceptance"]["gate_result"],
            )
            self.assertEqual(
                delivery_report["summary"]["completion_language_allowed"],
                summary["delivery_acceptance"]["completion_language_allowed"],
            )
            self.assertEqual(
                delivery_report["summary"]["readiness_state"],
                summary["delivery_acceptance"]["readiness_state"],
            )


if __name__ == "__main__":
    unittest.main()
