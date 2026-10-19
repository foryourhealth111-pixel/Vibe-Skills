from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_LEGACY_TDD_STATE_ALIASES = {
    "pass": "passing",
    "passed": "passing",
    "ok": "passing",
    "manual": "manual_review_required",
    "manual_required": "manual_review_required",
    "manual_review": "manual_review_required",
    "fail": "failing",
    "failed": "failing",
}


def resolve_tdd_evidence_state(payload: Mapping[str, Any]) -> str:
    states: list[str] = []
    for field in ("state", "status"):
        value = payload.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"TDD evidence {field} must be text")
        normalized = value.strip().casefold()
        normalized = _LEGACY_TDD_STATE_ALIASES.get(normalized, normalized)
        if normalized:
            states.append(normalized)
    if len(set(states)) > 1:
        raise ValueError("TDD evidence state and status fields conflict")
    return states[0] if states else ""
