from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface


def test_load_discoverable_entry_surface_reads_shared_wrapper_truth() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    assert surface.canonical_runtime_skill == 'vibe'
    assert surface.projected_skill_names == ['vibe']
    assert set(surface.entry_by_id) == {'vibe'}
    assert surface.grade_flags == ['--l', '--xl']
    assert surface.grade_flag_map['--l'] == 'L'
    assert surface.grade_flag_map['--xl'] == 'XL'
    assert surface.entry_by_id['vibe'].requested_stage_stop == 'phase_cleanup'
    assert surface.entry_by_id['vibe'].progressive_stage_stops == (
        'requirement_doc',
        'xl_plan',
        'phase_cleanup',
    )
    assert surface.entry_by_id['vibe'].publicly_exposed is True
    assert surface.entry_by_id['vibe'].allow_grade_flags is True
