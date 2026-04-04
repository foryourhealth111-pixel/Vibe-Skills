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
        mode='benchmark_autonomous',
        requested_skill='vibe',
    )

    assert [receipt['stage'] for receipt in result.stage_receipts] == EXPECTED_STAGES
    assert result.final_packet.stage == 'phase_cleanup'
    assert result.mode == 'interactive_governed'
    assert result.route['runtime_selected_skill'] == 'vibe'
    assert result.route['task_type'] == 'coding'
    assert result.plan['internal_grade'] == 'L'
