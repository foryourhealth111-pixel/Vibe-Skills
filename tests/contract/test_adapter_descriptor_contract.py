from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vgo_contracts.adapter_descriptor import AdapterDescriptor


def test_adapter_descriptor_requires_id() -> None:
    descriptor = AdapterDescriptor(id='codex', default_target_root='~/.codex')
    assert descriptor.id == 'codex'
