from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
for src in (CONTRACTS_SRC, RUNTIME_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_runtime.governance import normalize_runtime_mode
from vgo_runtime.stage_machine import RuntimeStageMachine


EXPECTED_STAGES = [
    'skeleton_check',
    'deep_interview',
    'requirement_doc',
    'xl_plan',
    'plan_execute',
    'phase_cleanup',
]


def test_runtime_stage_machine_order_is_fixed() -> None:
    machine = RuntimeStageMachine()
    assert list(machine.stages) == EXPECTED_STAGES


def test_runtime_stage_machine_rejects_unknown_stage() -> None:
    machine = RuntimeStageMachine()
    try:
        machine.index_of('unknown')
    except ValueError:
        assert True
    else:
        raise AssertionError('expected stage validation failure')


def test_runtime_stage_machine_none_stop_runs_to_terminal_stage() -> None:
    machine = RuntimeStageMachine()
    assert machine.iter_between('requirement_doc', None) == (
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup',
    )


def test_runtime_stage_machine_rejects_empty_stop_stage() -> None:
    machine = RuntimeStageMachine()
    try:
        machine.iter_between('skeleton_check', '')
    except ValueError:
        assert True
    else:
        raise AssertionError('expected empty stop stage validation failure')


def test_governance_mode_accepts_only_interactive_governed() -> None:
    assert normalize_runtime_mode('interactive_governed') == 'interactive_governed'
