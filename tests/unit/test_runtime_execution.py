from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
for src in (RUNTIME_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.runtime_packet import RuntimePacket
from vgo_runtime.execution import execute_runtime_packet
from vgo_runtime.kernel.work_binding import build_skill_usage_projection


def test_execute_runtime_packet_exposes_kernel_compatibility_data() -> None:
    packet = RuntimePacket(
        goal='design the architecture and write an implementation plan',
        stage='requirement_doc',
        entry_intent_id=None,
        requested_stage_stop='xl_plan',
    )

    result = execute_runtime_packet(packet)

    assert result.route['router_selected_skill'] == 'vibe'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert 'kernel' not in result.plan
    assert result.snapshot['task_card']['goal'] == packet.goal
    assert result.snapshot['candidates'] == []
    assert result.snapshot['work_plan']['task_id'] == result.snapshot['task_card']['id']
    assert result.snapshot['work_binding']['task_id'] == result.snapshot['task_card']['id']
    assert result.snapshot['effective_requested_stage_stop'] == 'xl_plan'
    assert result.snapshot['stage_stop_source'] == 'requested'
    assert result.snapshot['terminal_stage'] == 'xl_plan'
    assert result.snapshot['verification']['result'] == 'needs_execution'
    assert result.snapshot['work_plan']['work_units'][0]['bound_skill'] is None
    assert result.snapshot['work_binding']['units'][0]['bound_skill'] is None
    assert result.snapshot['work_results'][0]['artifact_paths']
    assert result.snapshot['work_results'][0]['execution_receipt_path'] is not None
    assert result.stage_receipts[0] == {'stage': 'requirement_doc', 'order': 1}


def test_execute_runtime_packet_keeps_requested_entry_but_reports_kernel_plan() -> None:
    packet = RuntimePacket(
        goal='implement the approved plan',
        stage='xl_plan',
        entry_intent_id='vibe',
        requested_stage_stop='phase_cleanup',
    )

    result = execute_runtime_packet(packet, requested_skill='vibe')

    assert result.route['requested_skill'] == 'vibe'
    assert result.route['router_selected_skill'] == 'vibe'
    assert result.snapshot['task_card']['mode'] == result.route['task_type']
    assert len(result.snapshot['work_plan']['work_units']) >= 1
    assert result.snapshot['work_results'][0]['status'] == 'needs_execution'


def test_execute_runtime_packet_uses_kernel_suggested_stage_stop_when_none_requested() -> None:
    packet = RuntimePacket(
        goal='design the architecture and write an implementation plan',
        stage='skeleton_check',
        entry_intent_id=None,
        requested_stage_stop=None,
    )

    result = execute_runtime_packet(packet)

    assert result.snapshot['work_plan']['work_units'][0]['preferred_skill'] is None
    assert result.snapshot['work_plan']['work_units'][0]['bound_skill'] is None
    assert 'kernel' not in result.plan
    assert result.snapshot['effective_requested_stage_stop'] == 'phase_cleanup'
    assert result.snapshot['stage_stop_source'] == 'kernel_suggested'
    assert result.snapshot['terminal_stage'] == 'phase_cleanup'
    assert result.final_packet.stage == 'phase_cleanup'
    assert result.snapshot['executed_stages'] == (
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup',
    )
    assert result.stage_receipts[0] == {'stage': 'skeleton_check', 'order': 1}
    assert [receipt['stage'] for receipt in result.stage_receipts] == [
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup',
    ]


def test_execute_runtime_packet_keeps_canonical_router_selection_when_only_entry_intent_exists() -> None:
    packet = RuntimePacket(
        goal='plan the migration and freeze the requirement before execution',
        stage='skeleton_check',
        entry_intent_id='vibe',
        requested_stage_stop='xl_plan',
    )

    result = execute_runtime_packet(packet)

    assert result.route['requested_skill'] == 'vibe'
    assert result.route['router_selected_skill'] == 'vibe'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert result.snapshot['task_card']['mode'] == 'planning'


def test_execute_runtime_packet_builds_final_packet_from_terminal_stage_once() -> None:
    packet = RuntimePacket(
        goal='implement the approved plan',
        stage='xl_plan',
        entry_intent_id='vibe',
        requested_stage_stop='phase_cleanup',
        requested_grade_floor='XL',
    )

    result = execute_runtime_packet(packet, requested_skill='vibe')

    assert result.final_packet.stage == result.snapshot['terminal_stage']
    assert result.final_packet.entry_intent_id == packet.entry_intent_id
    assert result.final_packet.requested_stage_stop == packet.requested_stage_stop
    assert result.final_packet.requested_grade_floor == packet.requested_grade_floor


def test_selected_skill_is_not_reported_as_used_without_artifact_evidence() -> None:
    usage = build_skill_usage_projection(
        work_binding={"units": [{"work_unit_id": "wu-1", "bound_skill": "code-review"}]},
        work_results=[
            {
                "work_unit_id": "wu-1",
                "used_skill": "code-review",
                "artifact_paths": [],
                "proof_artifact_paths": [],
            }
        ],
    )

    assert usage["bound"] == [{"skill_id": "code-review", "work_unit_id": "wu-1"}]
    assert usage["used"] == []
    assert usage["unused"] == [{"skill_id": "code-review", "work_unit_id": "wu-1"}]
    assert usage["evidence"] == []
