from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root


def _normalize_truth_state(state: str) -> str:
    normalized = str(state or "").strip().lower()
    aliases = {
        "pass": "passing",
        "passed": "passing",
        "ok": "passing",
        "manual": "manual_review_required",
        "manual_required": "manual_review_required",
        "manual_review": "manual_review_required",
        "fail": "failing",
        "failed": "failing",
    }
    return aliases.get(normalized, normalized)


def _truth_success(contract: dict[str, Any], state: str) -> bool:
    return bool(((contract.get("truth_states") or {}).get(state) or {}).get("counts_as_success"))


def _truth_completion_allowed(contract: dict[str, Any], state: str) -> bool:
    return bool(((contract.get("truth_states") or {}).get(state) or {}).get("completion_language_allowed"))


def _read_text_if_exists(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_bullets(text: str, heading: str) -> list[str]:
    section = _extract_section(text, heading)
    bullets: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _manual_spot_checks_from_requirement(requirement_text: str) -> tuple[list[str], bool]:
    raw_items = _extract_bullets(requirement_text, "Manual Spot Checks")
    if not raw_items:
        return [], True

    normalized_items = [item.strip() for item in raw_items if item.strip()]
    if len(normalized_items) == 1:
        lowered = normalized_items[0].lower()
        if lowered.startswith("none required") or lowered.startswith("no manual spot checks required"):
            return [], False

    return normalized_items, False


def _derive_readiness_state(gate_result: str, manual_spot_checks: list[str]) -> str:
    if gate_result == "PASS":
        return "fully_ready"
    if gate_result == "MANUAL_REVIEW_REQUIRED" or manual_spot_checks:
        return "manual_actions_pending"
    return "verification_failed"
