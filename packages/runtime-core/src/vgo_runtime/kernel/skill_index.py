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


INDEX_VERSION = 2
INDEX_SCHEMA_VERSION = "local_skill_index_v2"
CARD_SCHEMA_VERSION = "local_skill_capability_card_v1"
HOST_INSTALLED_SOURCE_KIND = "host_installed"
VIBE_LOCAL_SOURCE_KIND = "vibe_local"
SOURCE_ROOT_RELATIVE_PATH_CONTRACT = "source_root_relative"
CONTROLLER_SKILL_IDS = frozenset({"vibe"})
DISCOVERY_CHILD_DIRS = ("", "custom")
CAPABILITY_INFERENCE_HINTS = SKILL_INDEX_CAPABILITY_HINTS
ROUTING_BOUNDARY_HEADING = re.compile(r"^#{1,6}\s+Routing Boundary\s*$", re.IGNORECASE)
ROUTING_BOUNDARY_NOT_FOR = re.compile(r"\bThis is not\s+(.+?)(?:\.(?=\s|$)|。|$)", re.IGNORECASE)


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
    for child_dir in DISCOVERY_CHILD_DIRS:
        root = source_root / child_dir if child_dir else source_root
        if not root.exists():
            continue
        dirs.extend(sorted(path for path in root.iterdir() if path.is_dir()))
    return dirs


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
    capability_evidence = _build_capability_evidence(manifest, Path(manifest.skill_file))
    capabilities = _unique_ordered([str(row["capability"]) for row in capability_evidence])
    not_for = _unique_ordered([*manifest.not_for, *_extract_routing_boundary_not_for(Path(manifest.skill_file))])
    return {
        "skill_id": manifest.skill_id,
        "id": manifest.skill_id,
        "display_name": manifest.name,
        "name": manifest.name,
        "description": manifest.description,
        "capabilities": capabilities,
        "capability_evidence": capability_evidence,
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
        "native_skill_entrypoint": str(Path(manifest.skill_file).resolve()),
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


def _build_capability_evidence(manifest: object, skill_file: Path) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    declared = set(getattr(manifest, "capabilities"))
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
    body_lines = _skill_body_lines(skill_file)
    body_intent_text = "\n".join(
        line.casefold()
        for line in body_lines
        if _is_explicit_body_intent_line(line)
    )

    for capability, hints in CAPABILITY_INFERENCE_HINTS:
        if capability in declared:
            continue
        if any(hint in metadata_text for hint in hints):
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "metadata_text",
                    "strength": 0.7,
                }
            )
            continue
        if any(hint in body_intent_text for hint in hints):
            evidence.append(
                {
                    "capability": capability,
                    "evidence_level": "weak_text",
                    "source": "body_text",
                    "strength": 0.55,
                }
            )
    return evidence


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
    return lowered.startswith(("use this skill for ", "use for ", "use when ", "used when ", "用于", "适用于"))


def _skill_body_lines(skill_file: Path) -> list[str]:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return lines[index + 1 :]
    return lines


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
        "capabilities": list(entry.get("capabilities") or []),
        "capability_evidence": list(entry.get("capability_evidence") or []),
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
    for skill_dir in _discover_skill_dirs_for_source(source_spec):
        skill_id = skill_dir.name
        normalized_skill_id = _normalize_skill_id(skill_id)
        skill_file = skill_dir / "SKILL.md"
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
                "active_entrypoint": active["native_skill_entrypoint"],
                "inactive_entrypoints": [
                    row["native_skill_entrypoint"]
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
            str(row["native_skill_entrypoint"]),
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
