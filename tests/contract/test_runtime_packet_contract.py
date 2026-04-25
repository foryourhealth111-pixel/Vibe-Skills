from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vgo_contracts.runtime_packet import RuntimePacket


def test_runtime_packet_roundtrip() -> None:
    packet = RuntimePacket(
        goal='x',
        stage='deep_interview',
        entry_intent_id='vibe-how-do-we-do',
        requested_stage_stop='xl_plan',
        requested_grade_floor='XL',
    )
    restored = RuntimePacket.model_validate(packet.model_dump())
    assert restored == packet
    assert restored.model_dump() == packet.model_dump()
