from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
for src in (CONTRACTS_SRC, RUNTIME_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.runtime_packet import RuntimePacket
from vgo_runtime.execution import execute_runtime_packet


EXPECTED_STAGES = [
    'skeleton_check',
    'deep_interview',
    'requirement_doc',
    'xl_plan',
    'plan_execute',
    'phase_cleanup',
]


def test_runtime_packet_execution_runs_fixed_stage_sequence() -> None:
    result = execute_runtime_packet(
        RuntimePacket(goal='extract runtime core', stage='skeleton_check'),
        mode='interactive_governed',
        requested_skill='vibe',
    )

    assert [receipt['stage'] for receipt in result.stage_receipts] == EXPECTED_STAGES
    assert result.final_packet.stage == 'phase_cleanup'
    assert result.mode == 'interactive_governed'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert result.route['task_type'] == 'coding'
    assert result.plan['internal_grade'] == 'L'


def test_runtime_packet_execution_stops_after_requested_stage_stop() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal='produce requirement and plan only',
            stage='skeleton_check',
            entry_intent_id='vibe-how',
            requested_stage_stop='xl_plan',
        ),
        mode='interactive_governed',
        requested_skill='vibe-how',
    )

    assert [receipt['stage'] for receipt in result.stage_receipts] == [
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
    ]
    assert result.final_packet.stage == 'xl_plan'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert result.route['requested_skill'] == 'vibe-how'
    assert result.plan['stages'] == (
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
    )
    assert result.memory['stage_count'] == 4


def test_runtime_packet_execution_stops_after_requirement_freeze_for_vibe_want() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal='clarify the request and freeze requirements only',
            stage='skeleton_check',
            entry_intent_id='vibe-want',
            requested_stage_stop='requirement_doc',
        ),
        mode='interactive_governed',
        requested_skill='vibe-want',
    )

    assert [receipt['stage'] for receipt in result.stage_receipts] == [
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
    ]
    assert result.final_packet.stage == 'requirement_doc'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert result.route['requested_skill'] == 'vibe-want'
    assert result.plan['stages'] == (
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
    )
    assert result.memory['stage_count'] == 3


def test_runtime_packet_execution_applies_requested_grade_floor() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal='extract runtime core',
            stage='skeleton_check',
            entry_intent_id='vibe-do',
            requested_stage_stop='phase_cleanup',
            requested_grade_floor='XL',
        ),
        mode='interactive_governed',
        requested_skill='vibe-do',
    )

    assert result.plan['requested_grade_floor'] == 'XL'
    assert result.plan['requested_stage_stop'] == 'phase_cleanup'
    assert result.plan['internal_grade'] == 'XL'


def test_runtime_packet_execution_uses_entry_intent_when_requested_skill_is_omitted() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal='plan the migration and freeze the requirement before execution',
            stage='skeleton_check',
            entry_intent_id='vibe-how',
            requested_stage_stop='xl_plan',
        ),
        mode='interactive_governed',
    )

    assert result.route['requested_skill'] == 'vibe-how'
    assert result.route['router_selected_skill'] == 'vibe-how'
    assert result.route['runtime_selected_skill'] == 'vibe'
