from __future__ import annotations

import glob
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


def _resolve_evidence_path(value: str, *, workspace_root: Path, session_root: Path) -> Path:
    if value.startswith("session:"):
        relative = Path(value[len("session:"):])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("session evidence must stay inside the session root")
        resolved = (session_root / relative).resolve()
        if not resolved.is_relative_to(session_root.resolve()):
            raise ValueError("session evidence must stay inside the session root")
        return resolved
    path = Path(value)
    return (path if path.is_absolute() else workspace_root / path).resolve()


def _check_evidence_files(
    values: Any, *, workspace_root: Path, session_root: Path,
) -> tuple[set[Path], list[str]]:
    if values is None:
        return set(), []
    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
        return set(), ["Evidence paths must be a JSON array of non-empty strings."]
    files: set[Path] = set()
    notes: list[str] = []
    for value in values:
        try:
            path = _resolve_evidence_path(value, workspace_root=workspace_root, session_root=session_root)
            if not path.is_file():
                notes.append(f"Evidence is not a current file: {value}")
                continue
            with path.open("rb") as stream:
                stream.read(1)
            files.add(path)
        except (OSError, ValueError, RuntimeError) as exc:
            notes.append(f"Evidence is unreadable: {value} ({exc})")
    return files, notes


def _glob_output_files(value: str, *, workspace_root: Path, session_root: Path) -> set[Path]:
    session_relative = value.startswith("session:")
    pattern = value[len("session:"):] if session_relative else value
    root = session_root if session_relative else workspace_root
    path = Path(pattern)
    if path.is_absolute():
        matching_roots = [base.resolve() for base in (workspace_root, session_root) if path.is_relative_to(base.resolve())]
        root = max(matching_roots, key=lambda base: len(base.parts), default=Path(path.anchor))
        pattern = str(path.relative_to(root))
    files: set[Path] = set()
    for match in glob.glob(pattern, root_dir=root, recursive=True):
        candidate = root / match
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if session_relative and not resolved.is_relative_to(session_root.resolve()):
            raise ValueError("session evidence must stay inside the session root")
        files.add(resolved)
    return files


def _expected_output_evidence_notes(
    unit: dict[str, Any], evidence_files: set[Path], *, workspace_root: Path, session_root: Path,
) -> list[str]:
    if str(unit.get("write_scope") or "").strip().casefold() == "no task-file writes":
        return []
    notes: list[str] = []
    for value in _normalize_string_list(unit.get("expected_outputs")):
        # Plans also carry descriptive outcomes containing punctuation or path words.
        explicit_path = value.startswith(("session:", "./", "../", ".\\", "..\\")) or Path(value).is_absolute()
        if not explicit_path and any(char.isspace() for char in value):
            continue
        if not (explicit_path or glob.has_magic(value) or Path(value).suffix or "/" in value or "\\" in value):
            continue
        try:
            expected = _resolve_evidence_path(value, workspace_root=workspace_root, session_root=session_root)
            if expected in evidence_files:
                covered = True
            elif glob.has_magic(value):
                matches = _glob_output_files(value, workspace_root=workspace_root, session_root=session_root)
                covered = bool(matches) and matches.issubset(evidence_files)
            elif not Path(value).suffix and expected.is_dir():
                covered = any(path.is_relative_to(expected) for path in evidence_files)
            else:
                covered = expected in evidence_files
            if not covered:
                notes.append(f"Expected file output lacks current evidence: {value}")
        except (OSError, ValueError, RuntimeError) as exc:
            notes.append(f"Expected file output cannot be resolved: {value} ({exc})")
    return notes


def _normalize_skill_id_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]

    skill_ids: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            candidate = item.get("skill_id") or item.get("id") or item.get("name")
        else:
            candidate = item
        skill_id = str(candidate or "").strip()
        if not skill_id or skill_id in seen:
            continue
        seen.add(skill_id)
        skill_ids.append(skill_id)
    return skill_ids


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
    module_execution_path = session_root / "module-execution.json"
    if module_execution_path.exists():
        module_execution = load_json(module_execution_path)
        module_execution_payload = module_execution.get("tdd_evidence")
        if isinstance(module_execution_payload, dict) and module_execution_payload:
            payload = dict(module_execution_payload)
            payload["source_path"] = str(module_execution_path)
            return payload

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


def _invalid_optional_payload(path: Path, reason: str) -> dict[str, Any]:
    return {
        "__vgo_payload_state": "invalid",
        "source_path": str(path),
        "invalid_reason": reason,
    }


def _resolve_optional_payload(
    session_root: Path,
    execute_receipt: dict[str, Any],
    *,
    inline_key: str,
    explicit_path_key: str,
    sidecar_filename: str,
    inline_presence_keys: tuple[str, ...],
    report_invalid_payload: bool = False,
) -> dict[str, Any]:
    raw_inline_payload = execute_receipt.get(inline_key)
    inline_payload = raw_inline_payload or {}
    if isinstance(inline_payload, dict):
        has_inline_content = any(inline_payload.get(key) for key in inline_presence_keys)
        if has_inline_content:
            payload = dict(inline_payload)
            payload["source_path"] = str(session_root / "phase-execute.json")
            return payload
    elif report_invalid_payload and inline_key in execute_receipt and raw_inline_payload is not None:
        return _invalid_optional_payload(
            session_root / "phase-execute.json",
            f"{inline_key} payload was not a JSON object.",
        )

    explicit_path_value = str(execute_receipt.get(explicit_path_key) or "").strip()
    if explicit_path_value:
        resolved_session_root = session_root.resolve()
        explicit_path = Path(explicit_path_value)
        if not explicit_path.is_absolute():
            explicit_path = (resolved_session_root / explicit_path).resolve()
        else:
            explicit_path = explicit_path.resolve()

        path_in_session_scope = True
        try:
            explicit_path.relative_to(resolved_session_root)
        except ValueError:
            path_in_session_scope = False

        if path_in_session_scope and explicit_path.exists():
            try:
                payload = load_json(explicit_path)
            except Exception as exc:
                if report_invalid_payload:
                    return _invalid_optional_payload(explicit_path, f"Unable to parse JSON payload: {exc}")
                raise
            if isinstance(payload, dict):
                normalized_payload = dict(payload)
                normalized_payload["source_path"] = str(explicit_path)
                return normalized_payload
            if report_invalid_payload:
                return _invalid_optional_payload(explicit_path, "Payload was not a JSON object.")

    sidecar_path = session_root / sidecar_filename
    if sidecar_path.exists():
        try:
            payload = load_json(sidecar_path)
        except Exception as exc:
            if report_invalid_payload:
                return _invalid_optional_payload(sidecar_path, f"Unable to parse JSON payload: {exc}")
            raise
        if isinstance(payload, dict):
            normalized_payload = dict(payload)
            normalized_payload["source_path"] = str(sidecar_path)
            return normalized_payload
        if report_invalid_payload:
            return _invalid_optional_payload(sidecar_path, "Payload was not a JSON object.")

    return {}


def _derive_readiness_state(gate_result: str, manual_spot_checks: list[str]) -> str:
    if gate_result == "PASS":
        return "fully_ready"
    if gate_result == "PASS_DEGRADED":
        return "degraded_but_traceable"
    if gate_result == "MANUAL_REVIEW_REQUIRED" or manual_spot_checks:
        return "manual_actions_pending"
    return "verification_failed"
