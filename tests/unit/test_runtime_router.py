from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router import infer_task_type, load_allowed_vibe_entry_ids, route_runtime_task
from vgo_runtime.governance import choose_internal_grade


def test_runtime_router_allowed_entry_ids_match_shared_surface_contract() -> None:
    payload = json.loads((ROOT / 'config' / 'vibe-entry-surfaces.json').read_text(encoding='utf-8'))
    expected = frozenset(
        str(entry['id']).strip()
        for entry in payload['entries']
        if str(entry.get('id') or '').strip()
    )

    assert load_allowed_vibe_entry_ids() == expected


def test_runtime_router_rejects_entries_outside_shared_surface_contract() -> None:
    try:
        route_runtime_task('plan this change', requested_skill='vibe-xl')
    except ValueError:
        assert True
    else:
        raise AssertionError('expected unsupported entry id failure')


def test_runtime_router_infers_debug_from_keyword_style_router_prompt() -> None:
    task = 'router confidence-low fallback misroute task-classification grade-selection candidate-scoring'

    assert infer_task_type(task) == 'debug'


def test_runtime_router_infers_debug_for_dispatch_triage_prompts() -> None:
    assert infer_task_type('triage runtime specialist dispatch duplication') == 'debug'
    assert infer_task_type('root cause specialist dispatch duplication') == 'debug'


def test_runtime_router_avoids_suffix_fix_false_positive_for_docs_cleanup() -> None:
    assert infer_task_type('suffix cleanup in docs') == 'planning'


def test_runtime_router_avoids_codex_code_false_positive_for_docs_copy() -> None:
    assert infer_task_type('codex bootstrap wording in docs') == 'planning'


def test_runtime_router_keeps_clinical_grade_selection_prompt_as_planning() -> None:
    assert infer_task_type('clinical decision support grade selection evidence profile') == 'planning'


def test_runtime_router_keeps_ml_pipeline_prompt_as_planning() -> None:
    assert infer_task_type('ml pipeline workflow pack artifacts for deployment') == 'planning'


def test_runtime_governance_promotes_keyword_style_router_prompt_to_l() -> None:
    task = 'router confidence-low fallback misroute task-classification grade-selection candidate-scoring'

    assert choose_internal_grade('planning', task=task) == 'L'


def test_runtime_governance_keeps_docs_cleanup_prompt_at_m() -> None:
    assert choose_internal_grade('planning', task='suffix cleanup in docs') == 'M'


def test_runtime_governance_keeps_codex_docs_prompt_at_m() -> None:
    assert choose_internal_grade('planning', task='codex bootstrap wording in docs') == 'M'


def test_runtime_governance_keeps_microwave_docs_prompt_at_m() -> None:
    assert choose_internal_grade('planning', task='microwave prompt examples for docs') == 'M'


def test_runtime_governance_preserves_prd_backlog_quality_gate_as_l() -> None:
    assert choose_internal_grade('planning', task='create PRD and backlog with quality gate') == 'L'


def test_runtime_governance_promotes_install_to_runtime_rollout_to_xl() -> None:
    task = 'cross-host install to runtime end-to-end verification workflow'

    assert choose_internal_grade('planning', task=task) == 'XL'
