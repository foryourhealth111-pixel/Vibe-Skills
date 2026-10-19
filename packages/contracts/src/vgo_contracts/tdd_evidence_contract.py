from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def resolve_tdd_evidence_state(payload: Mapping[str, Any]) -> str:
    states: list[str] = []
    for field in ("state", "status"):
        value = payload.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"TDD evidence {field} must be text")
        normalized = value.strip().casefold()
        if normalized:
            states.append(normalized)
    if len(set(states)) > 1:
        raise ValueError("TDD evidence state and status fields conflict")
    return states[0] if states else ""
