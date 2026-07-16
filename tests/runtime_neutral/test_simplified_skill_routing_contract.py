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
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
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


class SimplifiedSkillRoutingContractTests(unittest.TestCase):
    def test_helper_builds_candidate_audit_without_selected_route_mirror(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$recommendations = @( "
            "[pscustomobject]@{ skill_id = 'scikit-learn'; reason = 'model training'; skill_entrypoint = 'skills/scikit/SKILL.md'; dispatch_phase = 'in_execution'; parallelizable_in_root_xl = $true }, "
            "[pscustomobject]@{ skill_id = 'plotly'; reason = 'optional charting'; skill_entrypoint = 'skills/plotly/SKILL.md'; dispatch_phase = 'post_execution'; parallelizable_in_root_xl = $false } "
            "); "
            "$hints = @([pscustomobject]@{ skill_id = 'matplotlib'; reason = 'legacy stage helper' }); "
            "$dispatch = [pscustomobject]@{ "
            "approved_dispatch = @($recommendations[0]); "
            "local_specialist_suggestions = @($recommendations[1]); "
            "blocked = @(); degraded = @() "
            "}; "
            "$routing = New-VibeSkillCandidateAudit "
            "-CandidateFocusSkill 'scikit-learn' "
            "-Recommendations @($recommendations) "
            "-StageAssistantHints @($hints) "
            "-SpecialistDispatch $dispatch; "
            "$routing | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual("simplified_skill_routing_v1", payload["schema_version"])
        candidate_ids = [item["skill_id"] for item in as_list(payload["candidates"])]
        rejected_ids = [item["skill_id"] for item in as_list(payload["rejected"])]
        self.assertNotIn("selected", payload)
        self.assertIn("scikit-learn", candidate_ids)
        self.assertIn("plotly", candidate_ids)
        self.assertIn("matplotlib", candidate_ids)
        self.assertIn("scikit-learn", rejected_ids)
        self.assertIn("plotly", rejected_ids)
        self.assertIn("matplotlib", rejected_ids)
        self.assertTrue(set(rejected_ids).issubset(candidate_ids))
        for row in [*as_list(payload["candidates"]), *as_list(payload["rejected"])]:
            self.assertEqual("candidate_only", row["bounded_role"])
            self.assertEqual("candidate_only", row["binding_profile"])
            self.assertEqual("not_applicable", row["dispatch_phase"])
            self.assertEqual("none", row["lane_policy"])
            self.assertEqual("none", row["write_scope"])
            self.assertEqual("none", row["review_mode"])
            self.assertEqual(0, row["execution_priority"])
            self.assertFalse(row["must_preserve_workflow"])

    def test_router_focus_without_a_matching_skill_record_is_not_executable(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$routing = New-VibeSkillCandidateAudit -CandidateFocusSkill 'documents'; "
            "$routing | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["documents"], [row["skill_id"] for row in as_list(payload["candidates"])])
        self.assertEqual(["documents"], [row["skill_id"] for row in as_list(payload["rejected"])])
        for row in [*as_list(payload["candidates"]), *as_list(payload["rejected"])]:
            self.assertEqual("candidate_only", row["bounded_role"])
            self.assertEqual("not_applicable", row["dispatch_phase"])
            self.assertEqual("none", row["write_scope"])
            self.assertNotIn("selected specialist workflow", row["task_slice"])

    def test_programmatic_skill_selection_helpers_are_removed_from_runtime_surface(self) -> None:
        runtime = SKILL_ROUTING_COMMON.read_text(encoding="utf-8")

        self.assertNotIn("function New-VibeSkillSelectionFromRouteResult", runtime)
        self.assertNotIn("function New-VibeWorkflowLevelSkillSelectionSchemes", runtime)
        self.assertNotIn("function New-VibeSkillRoutingFromLegacy", runtime)
        self.assertNotIn("RouterSelectedSkill", runtime)
        self.assertNotIn("skill_selection_v1", runtime)
        self.assertNotIn("shortlist_size", runtime)

    def test_selected_task_skill_ids_ignore_retired_skill_selection_mirror(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "skill_selection = [pscustomobject]@{ selected_skill_ids = @('retired-route-choice') }; "
            "module_assignments = [pscustomobject]@{ units = @([pscustomobject]@{ bound_skill = 'agent-confirmed-skill' }) } "
            "}; "
            "$ids = Get-VibeSelectedTaskSkillIds -RuntimeInputPacket $packet; "
            "[pscustomobject]@{ selected_skill_ids = $ids } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["agent-confirmed-skill"], as_list(payload["selected_skill_ids"]))

    def test_retired_route_selected_field_cannot_create_bound_skill_ids(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "skill_routing = [pscustomobject]@{ selected = @([pscustomobject]@{ skill_id = 'new-authority' }) }; "
            "specialist_dispatch = [pscustomobject]@{ approved_dispatch = @([pscustomobject]@{ skill_id = 'legacy-only' }) } "
            "}; "
            "$ids = Get-VibeBoundSkillIds -RuntimeInputPacket $packet; "
            "[pscustomobject]@{ selected_skill_ids = $ids } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual([], as_list(payload["selected_skill_ids"]))

    def test_selected_skill_ids_ignore_old_dispatch_when_skill_routing_is_absent(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "specialist_dispatch = [pscustomobject]@{ approved_dispatch = @([pscustomobject]@{ skill_id = 'legacy-skill' }) } "
            "}; "
            "$ids = Get-VibeBoundSkillIds -RuntimeInputPacket $packet; "
            "[pscustomobject]@{ selected_skill_ids = $ids } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual([], as_list(payload["selected_skill_ids"]))

    def test_router_result_is_candidate_and_confirm_data_not_work_truth(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"),
                "-Prompt",
                "Please use scikit-learn to compare tabular classification baselines.",
                "-Grade",
                "M",
                "-TaskType",
                "coding",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        route = json.loads(completed.stdout)

        self.assertEqual("candidate_discovery_only", route["router_contract_mode"])
        self.assertNotIn("module_assignments_truth_source", route)
        self.assertIsInstance(route["candidates"], list)
        self.assertNotIn("selected", route)
        self.assertNotIn("primary_candidate", route)
        self.assertNotIn("confirm_required", route)
        self.assertNotIn("confirm_options", route)
        self.assertNotIn("selected", route["skill_routing"])
        self.assertNotIn("primary_skill", route["skill_routing"])
        focus = route.get("candidate_focus")
        if isinstance(focus, dict):
            self.assertEqual("local_skill_index", focus["candidate_source"])
            self.assertTrue(str(focus["skill_entrypoint"]).endswith("SKILL.md"))

    def test_router_preserves_unicode_prompt_and_local_skill_paths(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory(prefix="vibe-用户-") as tempdir:
            home_root = Path(tempdir) / "家目录-羽裳"
            agent_root = home_root / ".agents"
            skill_root = agent_root / "skills" / "csv-analysis"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text(
                "---\n"
                "name: CSV Analysis\n"
                "description: Analyze CSV datasets, missing values, statistics, and charts.\n"
                "tags: [csv, data, analysis]\n"
                "---\n"
                "# CSV Analysis\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"),
                    "-Prompt",
                    "请冻结需求：分析一个CSV数据集并产出计划",
                    "-Grade",
                    "XL",
                    "-TaskType",
                    "planning",
                    "-HostId",
                    "codex",
                    "-TargetRoot",
                    str(agent_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            route = json.loads(completed.stdout)

        self.assertIn("请冻结需求", route["prompt"])
        self.assertNotIn("�", json.dumps(route, ensure_ascii=False))
        local_index = route["local_skill_index"]
        self.assertIn("羽裳", local_index["target_root"])
        candidate_paths = [
            str(item.get("skill_entrypoint") or "")
            for item in route["candidates"]
            if isinstance(item, dict)
        ]
        self.assertTrue(
            any("羽裳" in path and path.replace("\\", "/").endswith("csv-analysis/SKILL.md") for path in candidate_paths)
        )

    def test_requirement_freeze_keeps_route_candidates_out_of_module_assignments(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(FREEZE_SCRIPT),
                    "-Task",
                    "Build a scikit-learn tabular classification baseline and compare cross-validation metrics.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-simplified-skill-routing-freeze",
                    "-RequestedStageStop",
                    "requirement_doc",
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            self.assertIn("packet_path", completed.stdout)
            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        routing = packet["skill_routing"]
        module_assignments = packet["module_assignments"]
        self.assertEqual("runtime_input_freeze", packet["stage"])
        self.assertNotIn("skill_selection", packet)
        self.assertEqual("skill_search_guide_v1", packet["skill_search_guide"]["schema_version"])
        self.assertIn("explicit_only skills 只有在用户明确点名时才可入选", packet["skill_search_guide"]["selection_rules"])
        self.assertIn("不得跨越候选 skill 声明的负边界或适用限制", packet["skill_search_guide"]["selection_rules"])
        self.assertIn("没有 owner 时必须报缺口，不得伪装覆盖", packet["skill_search_guide"]["selection_rules"])
        self.assertIn("execute 阶段公开本次实际启用的 skills", packet["skill_search_guide"]["disclosure_rules"])
        self.assertNotIn("specialist_decision", packet)
        self.assertGreaterEqual(len(as_list(routing["candidates"])), 1)
        self.assertNotIn("selected", routing)
        self.assertEqual([], as_list(module_assignments["units"]))
        self.assertIsNone(packet["agent_skill_organization"])
        self.assertNotIn("confirm_required", packet["route_snapshot"])
        self.assertNotIn("confirm_required", packet["divergence_shadow"])

    def test_new_freeze_packet_omits_old_routing_compatibility_fields(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(FREEZE_SCRIPT),
                    "-Task",
                    "Use biopython to parse FASTA and summarize sequence lengths.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-skill-routing-legacy-isolation",
                    "-RequestedStageStop",
                    "requirement_doc",
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        self.assertIn("skill_routing", packet)
        self.assertIn("skill_search_guide", packet)
        self.assertIn("module_assignments", packet)
        self.assertNotIn("skill_usage", packet)
        self.assertNotIn("skill_selection", packet)
        self.assertEqual("compatibility_candidate_audit", packet["canonical_router"]["role"])
        self.assertEqual("vibe_runtime_with_agent_led_skill_search", packet["provenance"]["source_of_truth"])
        self.assertNotIn("legacy_skill_routing", packet)
        self.assertNotIn("stage_assistant_hints", packet)
        self.assertNotIn("specialist_recommendations", packet)
        self.assertNotIn("specialist_dispatch", packet)
