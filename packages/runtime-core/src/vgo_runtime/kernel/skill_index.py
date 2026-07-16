from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

from .capability_bridge import SKILL_INDEX_CAPABILITY_HINTS
from .host_skill_roots import resolve_host_skill_roots
from .skill_manifest import parse_installed_skill_manifest
from ..runtime_support import keyword_hit, normalize_text


INDEX_VERSION = 2
INDEX_SCHEMA_VERSION = "local_skill_index_v2"
CARD_SCHEMA_VERSION = "local_skill_capability_card_v2"
HOST_INSTALLED_SOURCE_KIND = "host_installed"
VIBE_LOCAL_SOURCE_KIND = "vibe_local"
SOURCE_ROOT_RELATIVE_PATH_CONTRACT = "source_root_relative"
CONTROLLER_SKILL_IDS = frozenset({"vibe"})
DISCOVERY_CHILD_DIRS = ("", "custom")
CAPABILITY_INFERENCE_HINTS = SKILL_INDEX_CAPABILITY_HINTS
ROUTING_BOUNDARY_HEADING = re.compile(r"^#{1,6}\s+Routing Boundary\s*$", re.IGNORECASE)
ROUTING_BOUNDARY_NOT_FOR = re.compile(r"\bThis is not\s+(.+?)(?:\.(?=\s|$)|。|$)", re.IGNORECASE)
WHEN_TO_USE_HEADING = re.compile(
    r"^#{1,6}\s+(when to use(?: this skill| vs alternatives)?|when this skill applies|use cases?|适用场景(?:（关键词）)?|何时使用)\s*$",
    re.IGNORECASE,
)
EXAMPLE_HEADING = re.compile(r"^#{1,6}\s+(examples?|示例|例子)\s*$", re.IGNORECASE)
PREREQUISITE_HEADING = re.compile(r"^#{1,6}\s+(prerequisites?|before you start|前置条件)\s*$", re.IGNORECASE)
DELIVERABLE_HEADING = re.compile(r"^#{1,6}\s+(deliverables?|outputs?|交付物|输出)\s*$", re.IGNORECASE)
EXPLICIT_ONLY_MARKERS = (
    "use only when the user explicitly asks",
    "only when the user explicitly asks",
    "user explicitly names this skill",
    "explicitly names this skill",
    "formal problem-pool construction is allowed only when",
)
ACTION_LED_INTENT_DESCRIPTION = re.compile(
    r"^(build|break|create|draft|design|diagnose|explain|extract|generate|help|humanize|implement|investigate|manage|optimize|organize|prepare|produce|query|read|review|search|summarize|teach|translate|turn|validate|write)\b",
    re.IGNORECASE,
)
DEPENDENCY_CONTEXT_MARKERS = (
    "according to ",
    "based on ",
    "compare against ",
    "compare the result against ",
    "derived from ",
    "from ",
    "result against ",
    "review against ",
    "using ",
    "with an existing ",
    "with existing ",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _vibe_root(agent_root: Path) -> Path:
    return agent_root.resolve() / "vibe"


def _ensure_runtime_dirs(agent_root: Path) -> Path:
    vibe_root = _vibe_root(agent_root)
    for relative_dir in ("generated", "runs"):
        (vibe_root / relative_dir).mkdir(parents=True, exist_ok=True)
    return vibe_root


def _normalize_skill_id(value: object) -> str:
    return str(value or "").strip().casefold()


def _source_priority(source_order: int) -> int:
    return source_order


def _source_spec(
    *,
    source_kind: str,
    source_root: str,
    resolved_source_root: Path,
    source_order: int,
) -> dict[str, object]:
    resolved = resolved_source_root.resolve()
    return {
        "source_kind": source_kind,
        "source_root": source_root,
        "resolved_source_root": str(resolved),
        "source_priority": _source_priority(source_order),
        "source_order": source_order,
        "path_contract": SOURCE_ROOT_RELATIVE_PATH_CONTRACT,
        "path_base": str(resolved),
    }


def _build_source_specs(vibe_root: Path, host_roots: tuple[Path, ...]) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    seen_roots: set[Path] = set()
    for host_root in host_roots:
        resolved = host_root.resolve()
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        specs.append(
            _source_spec(
                source_kind=HOST_INSTALLED_SOURCE_KIND,
                source_root=str(resolved),
                resolved_source_root=resolved,
                source_order=len(specs),
            )
        )

    vibe_local_root = vibe_root / "skills" / "local"
    if vibe_local_root.exists():
        specs.append(
            _source_spec(
                source_kind=VIBE_LOCAL_SOURCE_KIND,
                source_root="skills/local",
                resolved_source_root=vibe_local_root,
                source_order=len(specs),
            )
        )
    return specs


def _public_source_root(source_spec: dict[str, object]) -> dict[str, object]:
    return {
        "source_kind": source_spec["source_kind"],
        "source_root": source_spec["source_root"],
        "resolved_source_root": source_spec["resolved_source_root"],
        "source_priority": source_spec["source_priority"],
        "source_order": source_spec["source_order"],
    }


def _discover_skill_dirs_for_source(source_spec: dict[str, object]) -> list[Path]:
    source_root = Path(str(source_spec["resolved_source_root"]))
    dirs: list[Path] = []
    if not source_root.exists():
        return dirs
    if _is_codex_plugin_cache_root(source_root):
        return sorted({path.parent.resolve() for path in source_root.rglob("SKILL.md") if path.is_file()})
    for child_dir in DISCOVERY_CHILD_DIRS:
        root = source_root / child_dir if child_dir else source_root
        if not root.exists():
            continue
        dirs.extend(sorted(path for path in root.iterdir() if path.is_dir()))
    return dirs


def _is_codex_plugin_cache_root(path: Path) -> bool:
    resolved = path.resolve()
    return (
        resolved.name.casefold() == "cache"
        and resolved.parent.name.casefold() == "plugins"
        and resolved.parent.parent.name.casefold() == ".codex"
    )


def _relative_to_source(path: Path, source_spec: dict[str, object]) -> str:
    return path.resolve().relative_to(Path(str(source_spec["resolved_source_root"])).resolve()).as_posix()


def _invalid_entry(skill_id: str, source_spec: dict[str, object], reason: str, *, path: Path | None = None, message: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "skill_id": skill_id,
        "source_kind": source_spec["source_kind"],
        "source_root": source_spec["source_root"],
        "resolved_source_root": source_spec["resolved_source_root"],
        "source_priority": source_spec["source_priority"],
        "source_order": source_spec["source_order"],
        "reason": reason,
    }
    if path is not None:
        payload["path"] = str(path.resolve())
    if message:
        payload["message"] = message
    return payload


def _build_entry(*, skill_dir: Path, skill_file: Path, source_spec: dict[str, object]) -> dict[str, object]:
    manifest = parse_installed_skill_manifest(skill_file, skill_id=skill_dir.name)
    root_dir = _relative_to_source(Path(manifest.root_dir), source_spec)
    skill_file_value = _relative_to_source(Path(manifest.skill_file), source_spec)
    route_evidence_chunks = _build_route_evidence_chunks(manifest, Path(manifest.skill_file))
    explicit_only = _manifest_is_explicit_only(manifest, Path(manifest.skill_file))
    capability_evidence = _build_capability_evidence(manifest, Path(manifest.skill_file), route_evidence_chunks)
    capabilities = _route_active_capabilities(capability_evidence)
    not_for = _unique_ordered([*manifest.not_for, *_extract_routing_boundary_not_for(Path(manifest.skill_file))])
    return {
        "skill_id": manifest.skill_id,
        "id": manifest.skill_id,
        "display_name": manifest.name,
        "name": manifest.name,
        "description": manifest.description,
        "explicit_only": explicit_only,
        "capabilities": capabilities,
        "capability_evidence": capability_evidence,
        "route_evidence_chunks": route_evidence_chunks,
        "when_to_use": list(manifest.headings),
        "not_for": not_for,
        "outputs": [],
        "tags": list(manifest.tags),
        "enabled": True,
        "priority": 50,
        "root_dir": root_dir,
        "skill_file": skill_file_value,
        "resolved_root_dir": str(Path(manifest.root_dir).resolve()),
        "resolved_skill_file": str(Path(manifest.skill_file).resolve()),
        "skill_entrypoint": str(Path(manifest.skill_file).resolve()),
        "skill_root": str(Path(manifest.root_dir).resolve()),
        "path_contract": source_spec["path_contract"],
        "path_base": source_spec["path_base"],
        "source_kind": source_spec["source_kind"],
        "source_root": source_spec["source_root"],
        "resolved_source_root": source_spec["resolved_source_root"],
        "source_priority": source_spec["source_priority"],
        "source_order": source_spec["source_order"],
        "content_sha256": manifest.content_sha256,
        "active": False,
        "duplicate_state": "candidate",
    }


def _frontmatter_field_line_number(skill_file: Path, field_name: str) -> int | None:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return None
        if line.lstrip().startswith(f"{field_name}:"):
            return index
    return None


def _skill_body_line_rows(skill_file: Path) -> list[tuple[int, str]]:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return [(line_number, lines[line_number - 1]) for line_number in range(index + 2, len(lines) + 1)]
    return [(line_number, line) for line_number, line in enumerate(lines, start=1)]


def _section_kind_from_heading(line: str) -> str:
    stripped = line.strip()
    if WHEN_TO_USE_HEADING.match(stripped):
        return "when_to_use"
    if ROUTING_BOUNDARY_HEADING.match(stripped):
        return "routing_boundary"
    if EXAMPLE_HEADING.match(stripped):
        return "example"
    if PREREQUISITE_HEADING.match(stripped):
        return "prerequisite"
    if DELIVERABLE_HEADING.match(stripped):
        return "deliverable"
    return "background"


def _classify_route_evidence_role(text: str, *, section_kind: str) -> str:
    lowered = str(text or "").strip().casefold()
    if not lowered:
        return "background"
    if section_kind == "routing_boundary" or lowered.startswith(("this is not ", "do not use this skill for", "do not use for", "not for ")):
        return "not_applicable"
    if section_kind == "example" or lowered.startswith(("example:", "- example:", "* example:")):
        return "example"
    if section_kind == "prerequisite":
        return "prerequisite"
    if section_kind == "deliverable":
        return "deliverable"
    if section_kind == "when_to_use" or _is_explicit_body_intent_line(text):
        return "applicable"
    return "background"


def _route_evidence_source(*, section_kind: str, role: str) -> str:
    if role == "not_applicable":
        return "body.routing_boundary"
    if role == "example":
        return "body.example"
    if role == "prerequisite":
        return "body.prerequisite"
    if role == "deliverable":
        return "body.deliverable"
    if role == "applicable":
        return "body.intent"
    return f"body.{section_kind}"


def _build_route_evidence_chunks(manifest: object, skill_file: Path) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    description = str(getattr(manifest, "description") or "").strip()
    if description:
        description_line = _frontmatter_field_line_number(skill_file, "description")
        chunks.append(
            {
                "text": description,
                "role": "applicable" if _contains_explicit_intent_phrase(description) else "background",
                "source": "frontmatter.description",
                "line_start": int(description_line or 1),
                "line_end": int(description_line or 1),
            }
        )

    section_kind = "background"
    in_code_fence = False
    for line_number, line in _skill_body_line_rows(skill_file):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or not stripped:
            continue
        if stripped.startswith("#"):
            section_kind = _section_kind_from_heading(stripped)
            continue
        role = _classify_route_evidence_role(line, section_kind=section_kind)
        chunks.append(
            {
                "text": stripped,
                "role": role,
                "source": _route_evidence_source(section_kind=section_kind, role=role),
                "line_start": line_number,
                "line_end": line_number,
            }
        )
    return chunks


def _build_capability_evidence(
    manifest: object,
    skill_file: Path,
    route_evidence_chunks: list[dict[str, object]],
) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    declared = set(getattr(manifest, "capabilities"))
    explicit_only = _manifest_is_explicit_only(manifest, skill_file)
    identity_text = " ".join(
        [
            str(getattr(manifest, "skill_id")),
            str(getattr(manifest, "name")),
        ]
    ).casefold()
    for capability in getattr(manifest, "capabilities"):
        evidence.append(
            {
                "capability": capability,
                "evidence_level": "declared",
                "source": "frontmatter",
                "strength": 1.0,
            }
        )

    metadata_text = " ".join(
        [
            str(getattr(manifest, "skill_id")),
            str(getattr(manifest, "name")),
            str(getattr(manifest, "description")),
            " ".join(getattr(manifest, "tags")),
            " ".join(getattr(manifest, "headings")),
        ]
    ).casefold()
    frontmatter_intent_lines = [
        str(chunk.get("text") or "")
        for chunk in route_evidence_chunks
        if str(chunk.get("role") or "") == "applicable" and str(chunk.get("source") or "").startswith("frontmatter.")
    ]
    body_intent_lines = [
        str(chunk.get("text") or "")
        for chunk in route_evidence_chunks
        if str(chunk.get("role") or "") == "applicable" and str(chunk.get("source") or "").startswith("body.")
    ]

    for capability, hints in CAPABILITY_INFERENCE_HINTS:
        if capability in declared:
            continue
        intent_hints = hints
        identity_match = any(keyword_hit(identity_text, hint) for hint in hints)
        metadata_match = any(keyword_hit(metadata_text, hint) for hint in hints)
        frontmatter_intent_match = any(
            _intent_text_matches_hint_as_owner(line, hint)
            for line in frontmatter_intent_lines
            for hint in intent_hints
        )
        body_match = any(
            _intent_text_matches_hint_as_owner(line, hint)
            for line in body_intent_lines
            for hint in intent_hints
        )
        requires_capability_anchor = capability in {"presentation.deck", "visualization.figure"}
        allow_intent_inference = not requires_capability_anchor or identity_match or metadata_match
        if identity_match:
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "identity_text",
                    "strength": 0.85,
                }
            )
        if metadata_match and not explicit_only:
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "metadata_text",
                    "strength": 0.7,
                }
            )
        if frontmatter_intent_match and not explicit_only and allow_intent_inference:
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "frontmatter_intent",
                    "strength": 0.6,
                }
            )
        if body_match and not explicit_only and allow_intent_inference:
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "body_text",
                    "strength": 0.55,
                }
            )
    return evidence


def _manifest_is_explicit_only(manifest: object, skill_file: Path) -> bool:
    text_parts: list[str] = []
    description = str(getattr(manifest, "description") or "").strip()
    if description:
        text_parts.append(description)
    for line in getattr(manifest, "when_to_use", ()) or ():
        text = str(line).strip()
        if text:
            text_parts.append(text)
    text_parts.extend(line.strip() for line in _skill_body_lines(skill_file)[:80] if line.strip())
    lowered = "\n".join(text_parts).casefold()
    return any(marker in lowered for marker in EXPLICIT_ONLY_MARKERS)


def _route_active_capabilities(capability_evidence: list[dict[str, object]]) -> list[str]:
    active: list[str] = []
    for row in capability_evidence:
        capability = str(row.get("capability") or "").strip()
        if not capability:
            continue
        evidence_level = str(row.get("evidence_level") or "").strip()
        source = str(row.get("source") or "").strip()
        if evidence_level == "weak_text" and source == "metadata_text":
            continue
        active.append(capability)
    return _unique_ordered(active)


def _body_intent_lines(skill_file: Path) -> list[str]:
    lines: list[str] = []
    in_code_fence = False
    in_when_to_use_section = False
    for line in _skill_body_lines(skill_file):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if stripped.startswith("#"):
            in_when_to_use_section = bool(WHEN_TO_USE_HEADING.match(stripped))
            continue
        if _is_explicit_body_intent_line(line):
            lines.append(line)
            continue
        if in_when_to_use_section and stripped:
            lines.append(line)
    return lines


def _frontmatter_intent_text(manifest: object) -> str:
    lines: list[str] = []
    description = str(getattr(manifest, "description") or "").strip()
    if description and _contains_explicit_intent_phrase(description):
        lines.append(description)
    for line in getattr(manifest, "when_to_use", ()) or ():
        text = str(line).strip()
        if text:
            lines.append(text)
    return "\n".join(text.casefold() for text in lines)


def _contains_explicit_intent_phrase(text: str) -> bool:
    lowered = str(text or "").casefold()
    if not lowered:
        return False
    if any(marker in lowered for marker in ("use this skill for ", "use for ", "use when ", "used when ", "用于", "适用于")):
        return True
    if "时使用" in lowered and any(anchor in lowered for anchor in ("用户", "当用户", "用户说", "用户要求", "需要")):
        return True
    if ACTION_LED_INTENT_DESCRIPTION.match(str(text or "").strip()):
        return True
    return re.search(r"\buse the .+ skill (when|for)\b", lowered) is not None


def _intent_text_matches_hint_as_owner(text: str, hint: str) -> bool:
    lowered = normalize_text(text)
    hint_lower = normalize_text(hint)
    if not lowered or not hint_lower or not keyword_hit(lowered, hint_lower):
        return False
    hint_index = lowered.find(hint_lower)
    if hint_index < 0:
        return True
    prefix = lowered[max(0, hint_index - 48):hint_index]
    return not any(marker in prefix for marker in DEPENDENCY_CONTEXT_MARKERS)


def _is_explicit_body_intent_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    while stripped.startswith(("-", "*")):
        stripped = stripped[1:].lstrip()
    while stripped.startswith("#"):
        stripped = stripped[1:].lstrip()
    stripped = stripped.lstrip("*_`").strip()
    lowered = stripped.casefold()
    return lowered.startswith(("use this skill for ", "use for ", "use when ", "used when ", "用于", "适用于")) or (
        "时使用" in lowered and any(anchor in lowered for anchor in ("用户", "当用户", "用户说", "用户要求", "需要"))
    ) or bool(re.match(r"^use the .+ skill (when|for)\b", lowered))


def _skill_body_lines(skill_file: Path) -> list[str]:
    return [line for _, line in _skill_body_line_rows(skill_file)]


def _extract_routing_boundary_not_for(skill_file: Path) -> list[str]:
    body_lines = _skill_body_lines(skill_file)
    in_routing_boundary = False
    phrases: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if ROUTING_BOUNDARY_HEADING.match(stripped):
            in_routing_boundary = True
            continue
        if in_routing_boundary and stripped.startswith("#"):
            break
        if not in_routing_boundary or not stripped:
            continue
        match = ROUTING_BOUNDARY_NOT_FOR.search(stripped)
        if match is None:
            continue
        for phrase in re.split(r",|\bor\b", match.group(1)):
            text = phrase.strip(" .;:,-")
            if text:
                phrases.append(text)
    return _unique_ordered(phrases)


def _card_file_name(skill_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", skill_id.strip())
    return f"{safe or 'skill'}.json"


def _skill_card_payload(entry: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "skill_id": entry["skill_id"],
        "name": entry["name"],
        "description": entry["description"],
        "explicit_only": bool(entry.get("explicit_only")),
        "capabilities": list(entry.get("capabilities") or []),
        "capability_evidence": list(entry.get("capability_evidence") or []),
        "route_evidence_chunks": list(entry.get("route_evidence_chunks") or []),
        "not_for": list(entry.get("not_for") or []),
        "tags": list(entry.get("tags") or []),
        "headings": list(entry.get("when_to_use") or []),
        "source_kind": entry["source_kind"],
        "source_root": entry["source_root"],
        "root_dir": entry["root_dir"],
        "skill_file": entry["skill_file"],
        "content_sha256": entry["content_sha256"],
    }


def _load_card(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _write_card(path: Path, payload: dict[str, object]) -> None:
    previous_mtime = path.stat().st_mtime_ns if path.exists() else None
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if previous_mtime is not None and path.stat().st_mtime_ns <= previous_mtime:
        os.utime(path, ns=(previous_mtime + 1, previous_mtime + 1))


def _build_skill_cache(vibe_root: Path, entries: list[dict[str, object]]) -> dict[str, object]:
    cards_dir = vibe_root / "generated" / "skill-cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    cards: list[dict[str, object]] = []
    reused_count = 0
    refreshed_count = 0

    for entry in entries:
        if not bool(entry.get("active")):
            continue
        skill_id = str(entry["skill_id"])
        card_path = cards_dir / _card_file_name(skill_id)
        payload = _skill_card_payload(entry)
        existing = _load_card(card_path)
        reused = existing == payload
        if reused:
            reused_count += 1
        else:
            _write_card(card_path, payload)
            refreshed_count += 1
        entry["capability_card_path"] = str(card_path.resolve())
        cards.append(
            {
                "skill_id": skill_id,
                "card_path": str(card_path.resolve()),
                "content_sha256": payload["content_sha256"],
                "reused": reused,
            }
        )

    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "cards_dir": str(cards_dir.resolve()),
        "cards": cards,
        "reused_count": reused_count,
        "refreshed_count": refreshed_count,
    }


def _load_source_entries(source_spec: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    entries: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    skill_dirs = _discover_skill_dirs_for_source(source_spec)
    ambiguous_plugin_ids: set[str] = set()
    if _is_codex_plugin_cache_root(Path(str(source_spec["resolved_source_root"]))):
        counts: dict[str, int] = {}
        for skill_dir in skill_dirs:
            skill_id = _normalize_skill_id(skill_dir.name)
            counts[skill_id] = counts.get(skill_id, 0) + 1
        ambiguous_plugin_ids = {skill_id for skill_id, count in counts.items() if skill_id and count > 1}

    for skill_dir in skill_dirs:
        skill_id = skill_dir.name
        normalized_skill_id = _normalize_skill_id(skill_id)
        skill_file = skill_dir / "SKILL.md"
        if normalized_skill_id in ambiguous_plugin_ids:
            diagnostics.append(
                _invalid_entry(
                    skill_id,
                    source_spec,
                    "ambiguous_plugin_skill_id",
                    path=skill_file,
                    message=f"Multiple cached plugin Skills use id {skill_id!r}",
                )
            )
            continue
        if normalized_skill_id in CONTROLLER_SKILL_IDS:
            diagnostics.append(_invalid_entry(skill_id, source_spec, "controller_entry_excluded", path=skill_file))
            continue
        if not skill_file.is_file():
            diagnostics.append(_invalid_entry(skill_id, source_spec, "missing_skill_md", path=skill_file))
            continue
        try:
            entries.append(_build_entry(skill_dir=skill_dir, skill_file=skill_file, source_spec=source_spec))
        except ValueError as exc:
            reason = "missing_required_frontmatter" if "missing required frontmatter field" in str(exc) else "invalid_frontmatter"
            diagnostics.append(_invalid_entry(skill_id, source_spec, reason, path=skill_file, message=str(exc)))
    return entries, diagnostics


def _apply_duplicate_resolution(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    active_ids: set[str] = set()
    for entry in entries:
        skill_id = _normalize_skill_id(entry.get("skill_id"))
        if skill_id and skill_id not in active_ids:
            entry["active"] = True
            entry["duplicate_state"] = "active"
            active_ids.add(skill_id)
        else:
            entry["active"] = False
            entry["duplicate_state"] = "shadowed_duplicate"
    return entries


def _duplicate_diagnostics(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    by_id: dict[str, list[dict[str, object]]] = {}
    for entry in entries:
        by_id.setdefault(_normalize_skill_id(entry.get("skill_id")), []).append(entry)
    diagnostics: list[dict[str, object]] = []
    for skill_id, rows in sorted(by_id.items()):
        if not skill_id or len(rows) <= 1:
            continue
        active = next(row for row in rows if bool(row.get("active")))
        diagnostics.append(
            {
                "skill_id": skill_id,
                "active_entrypoint": active["skill_entrypoint"],
                "inactive_entrypoints": [
                    row["skill_entrypoint"]
                    for row in rows
                    if not bool(row.get("active"))
                ],
                "resolution": "first_root_wins",
            }
        )
    return diagnostics


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_skill_catalog(*, agent_root: Path, host_roots: tuple[Path, ...] = ()) -> dict[str, object]:
    vibe_root = _ensure_runtime_dirs(agent_root)
    source_specs = _build_source_specs(vibe_root, host_roots)
    entries: list[dict[str, object]] = []
    invalid_entries: list[dict[str, object]] = []

    for source_spec in source_specs:
        source_entries, source_invalid = _load_source_entries(source_spec)
        entries.extend(source_entries)
        invalid_entries.extend(source_invalid)

    entries.sort(
        key=lambda row: (
            int(row["source_priority"]),
            int(row["source_order"]),
            str(row["skill_id"]),
            str(row["skill_entrypoint"]),
        )
    )
    _apply_duplicate_resolution(entries)
    skill_cache = _build_skill_cache(vibe_root, entries)
    duplicate_rows = _duplicate_diagnostics(entries)
    active_source_roots = [
        _public_source_root(source_spec)
        for source_spec in source_specs
        if any(
            entry["active"]
            and entry["source_kind"] == source_spec["source_kind"]
            and entry["source_root"] == source_spec["source_root"]
            for entry in entries
        )
    ]

    return {
        "version": INDEX_VERSION,
        "schema_version": INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "roots": [str(source_spec["source_root"]) for source_spec in source_specs],
        "host_roots": [str(path.resolve()) for path in host_roots],
        "catalog_source_kinds": _unique_ordered(
            [str(source_spec["source_kind"]) for source_spec in source_specs]
        ),
        "catalog_source_roots": [_public_source_root(source_spec) for source_spec in source_specs],
        "active_source_kinds": _unique_ordered(
            [str(source_root["source_kind"]) for source_root in active_source_roots]
        ),
        "active_source_roots": active_source_roots,
        "discovery_diagnostics": {
            "invalid_entries": invalid_entries,
            "duplicates": duplicate_rows,
        },
        "skill_cache": skill_cache,
        "entries": entries,
    }


def _build_skill_index_payload(catalog: dict[str, object]) -> dict[str, object]:
    entries = [entry for entry in catalog["entries"] if entry["active"]]
    return {
        "version": INDEX_VERSION,
        "schema_version": INDEX_SCHEMA_VERSION,
        "generated_at": catalog["generated_at"],
        "roots": list(catalog["roots"]),
        "host_roots": list(catalog.get("host_roots") or []),
        "catalog_source_kinds": list(catalog["catalog_source_kinds"]),
        "catalog_source_roots": list(catalog["catalog_source_roots"]),
        "active_source_kinds": list(catalog["active_source_kinds"]),
        "active_source_roots": list(catalog["active_source_roots"]),
        "discovery_diagnostics": dict(catalog["discovery_diagnostics"]),
        "skill_cache": dict(catalog["skill_cache"]),
        "skills": entries,
    }


def build_skill_index_from_catalog(catalog: dict[str, object]) -> dict[str, object]:
    return _build_skill_index_payload(catalog)


def build_skill_index(agent_root: Path, *, host_roots: tuple[Path, ...] = ()) -> dict[str, object]:
    catalog = build_skill_catalog(agent_root=agent_root, host_roots=host_roots)
    return build_skill_index_from_catalog(catalog)


def write_skill_catalog(agent_root: Path, payload: dict[str, object]) -> Path:
    vibe_root = _ensure_runtime_dirs(agent_root)
    catalog_path = vibe_root / "generated" / "skills-catalog.json"
    catalog_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return catalog_path


def write_skill_index(agent_root: Path, payload: dict[str, object]) -> Path:
    vibe_root = _ensure_runtime_dirs(agent_root)
    index_path = vibe_root / "generated" / "skills-index.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index_path


def load_skill_index(agent_root: Path) -> dict[str, object]:
    index_path = _vibe_root(agent_root) / "generated" / "skills-index.json"
    return json.loads(index_path.read_text(encoding="utf-8"))


def discover_skill_files(agent_root: Path) -> list[Path]:
    vibe_root = _ensure_runtime_dirs(agent_root)
    source_specs = _build_source_specs(vibe_root, ())
    files: list[Path] = []
    for source_spec in source_specs:
        for skill_dir in _discover_skill_dirs_for_source(source_spec):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.is_file():
                files.append(skill_file.resolve())
    return sorted(files)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-root", required=True)
    parser.add_argument("--host-id")
    parser.add_argument("--workspace-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    agent_root = Path(args.agent_root).resolve()
    workspace_root = Path(args.workspace_root).resolve() if args.workspace_root else None
    host_roots: tuple[Path, ...] = ()
    if args.host_id:
        host_roots = tuple(
            root.path
            for root in resolve_host_skill_roots(
                repo_root=_repo_root(),
                host_id=args.host_id,
                agent_root=agent_root,
                workspace_root=workspace_root,
            )
        )
    catalog = build_skill_catalog(agent_root=agent_root, host_roots=host_roots)
    catalog_path = write_skill_catalog(agent_root, catalog)
    payload = build_skill_index_from_catalog(catalog)
    index_path = write_skill_index(agent_root, payload)
    result: dict[str, Any] = {
        "agent_root": str(agent_root),
        "host_id": str(args.host_id).strip().lower() if args.host_id else None,
        "workspace_root": str(workspace_root) if workspace_root is not None else None,
        "host_roots": [str(path) for path in host_roots],
        "catalog_path": str(catalog_path),
        "catalog_count": len(catalog["entries"]),
        "index_path": str(index_path),
        "skill_count": len(payload["skills"]),
        "skills": payload["skills"],
        "discovery_diagnostics": payload["discovery_diagnostics"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
