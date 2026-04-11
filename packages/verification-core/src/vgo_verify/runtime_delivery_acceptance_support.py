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


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def _normalize_match_key(value: str) -> str:
    return " ".join(str(value).split()).strip().lower()


def _missing_frozen_items(required_items: list[str], covered_items: list[str]) -> list[str]:
    covered_keys = {_normalize_match_key(item) for item in _normalize_string_list(covered_items)}
    missing: list[str] = []
    for item in _normalize_string_list(required_items):
        if _normalize_match_key(item) not in covered_keys:
            missing.append(item)
    return missing


def _requirement_optional_bullets(requirement_text: str, heading: str) -> list[str]:
    return _normalize_string_list(_extract_bullets(requirement_text, heading))


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


def _resolve_artifact_review_payload(session_root: Path, execute_receipt: dict[str, Any]) -> dict[str, Any]:
    return _resolve_optional_payload(
        session_root,
        execute_receipt,
        inline_key="artifact_review",
        explicit_path_key="artifact_review_path",
        sidecar_filename="artifact-review.json",
        inline_presence_keys=("status", "state", "evidence_paths", "notes"),
    )


def _resolve_tdd_evidence_payload(session_root: Path, execute_receipt: dict[str, Any]) -> dict[str, Any]:
    return _resolve_optional_payload(
        session_root,
        execute_receipt,
        inline_key="tdd_evidence",
        explicit_path_key="tdd_evidence_path",
        sidecar_filename="tdd-evidence.json",
        inline_presence_keys=(
            "status",
            "state",
            "evidence_paths",
            "notes",
            "red_phase_evidence_paths",
            "green_phase_evidence_paths",
            "refactor_phase_evidence_paths",
            "covered_code_task_tdd_evidence_requirements",
            "covered_code_task_tdd_exceptions",
        ),
    )


def _resolve_optional_payload(
    session_root: Path,
    execute_receipt: dict[str, Any],
    *,
    inline_key: str,
    explicit_path_key: str,
    sidecar_filename: str,
    inline_presence_keys: tuple[str, ...],
) -> dict[str, Any]:
    inline_payload = execute_receipt.get(inline_key) or {}
    if isinstance(inline_payload, dict):
        has_inline_content = any(inline_payload.get(key) for key in inline_presence_keys)
        if has_inline_content:
            payload = dict(inline_payload)
            payload["source_path"] = str(session_root / "phase-execute.json")
            return payload

    explicit_path_value = str(execute_receipt.get(explicit_path_key) or "").strip()
    if explicit_path_value:
        explicit_path = Path(explicit_path_value)
        if not explicit_path.is_absolute():
            explicit_path = (session_root / explicit_path).resolve()
        if explicit_path.exists():
            payload = load_json(explicit_path)
            if isinstance(payload, dict):
                normalized_payload = dict(payload)
                normalized_payload["source_path"] = str(explicit_path)
                return normalized_payload

    sidecar_path = session_root / sidecar_filename
    if sidecar_path.exists():
        payload = load_json(sidecar_path)
        if isinstance(payload, dict):
            normalized_payload = dict(payload)
            normalized_payload["source_path"] = str(sidecar_path)
            return normalized_payload

    return {}


def _derive_readiness_state(gate_result: str, manual_spot_checks: list[str]) -> str:
    if gate_result == "PASS":
        return "fully_ready"
    if gate_result == "MANUAL_REVIEW_REQUIRED" or manual_spot_checks:
        return "manual_actions_pending"
    return "verification_failed"
