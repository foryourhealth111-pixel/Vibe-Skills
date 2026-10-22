from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_EVIDENCE_STATE_ALIASES = {
    "pass": "passing",
    "passed": "passing",
    "ok": "passing",
    "manual": "manual_review_required",
    "manual_required": "manual_review_required",
    "manual_review": "manual_review_required",
    "fail": "failing",
    "failed": "failing",
}


def normalize_evidence_state(value: str) -> str:
    normalized = value.strip().casefold()
    return _EVIDENCE_STATE_ALIASES.get(normalized, normalized)


def resolve_evidence_state(payload: Mapping[str, Any], *, label: str = "Evidence") -> str:
    states: list[str] = []
    for field in ("state", "status"):
        value = payload.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"{label} {field} must be text")
        normalized = normalize_evidence_state(value)
        if normalized:
            states.append(normalized)
    if len(set(states)) > 1:
        raise ValueError(f"{label} state and status fields conflict")
    return states[0] if states else ""


def resolve_tdd_evidence_state(payload: Mapping[str, Any]) -> str:
    return resolve_evidence_state(payload, label="TDD evidence")
