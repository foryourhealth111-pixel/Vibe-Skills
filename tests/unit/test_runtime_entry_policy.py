from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = ROOT / "packages" / "contracts" / "src"
for src in (RUNTIME_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_runtime.entry_policy import load_runtime_entry_surface, resolve_runtime_task_type, suggest_stage_stop


def test_runtime_entry_policy_uses_shared_discoverable_entry_surface() -> None:
    surface = load_runtime_entry_surface()

    assert surface.canonical_runtime_skill == "vibe"
    assert set(surface.entry_by_id) == {"vibe"}


def test_runtime_entry_policy_preserves_requested_task_type_for_canonical_vibe() -> None:
    assert resolve_runtime_task_type("planning", requested_entry_id="vibe") == "planning"
    assert resolve_runtime_task_type("coding", requested_entry_id="vibe") == "coding"


def test_runtime_entry_policy_uses_shared_entry_surface_for_stage_stop() -> None:
    assert suggest_stage_stop("vibe") == "phase_cleanup"
    assert suggest_stage_stop("retired-entry-id") == "phase_cleanup"
