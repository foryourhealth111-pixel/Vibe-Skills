from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from vgo_contracts.canonical_vibe_contract import resolve_canonical_vibe_contract, uses_skill_only_activation
from vgo_contracts.discoverable_entry_surface import DiscoverableEntry, DiscoverableEntrySurface


@dataclass(frozen=True, slots=True)
class WrapperDescriptor:
    entry_id: str
    relpath: Path
    content: str


def _host_wrapper_relpath(host_id: str, entry: DiscoverableEntry) -> Path:
    normalized = (host_id or "").strip().lower()
    if normalized != "opencode" and uses_skill_only_activation(normalized):
        return Path("skills") / entry.id / "SKILL.md"
    return Path("commands") / f"{entry.id}.md"


def _frontmatter_lines(host_id: str, entry: DiscoverableEntry, *, relpath: Path) -> list[str]:
    lines = ["---"]
    if relpath.name == "SKILL.md":
        lines.extend(
            [
                f"name: {entry.id}",
                "description: >-",
                f"  Launch {entry.display_name} through the canonical governed Vibe runtime.",
            ]
        )
    else:
        lines.append(f"description: Launch {entry.display_name} through the canonical governed Vibe runtime.")
    if host_id == "opencode":
        lines.append("agent: vibe-plan")
    lines.append("---")
    return lines


def _wrapper_contract(host_id: str) -> dict[str, object]:
    normalized = (host_id or "").strip().lower()
    try:
        return resolve_canonical_vibe_contract(None, normalized)
    except ValueError:
        return {
            "host_id": normalized,
            "entry_mode": "bridged_runtime",
            "fallback_policy": "blocked",
            "proof_required": True,
            "allow_skill_doc_fallback": False,
            "launcher_kind": "managed_bridge",
            "supports_bounded_stop": True,
        }


def _body_lines(host_id: str, entry: DiscoverableEntry, *, contract: dict[str, object]) -> list[str]:
    grade_line = "yes" if entry.allow_grade_flags else "no"
    stop_stage = entry.requested_stage_stop
    bounded_warning = (
        f"Stop at `{stop_stage}` and re-enter through canonical `vibe` or another approved wrapper to continue later stages."
        if stop_stage != "phase_cleanup"
        else "Continue through `phase_cleanup` without creating a second runtime authority."
    )
    trampoline_payload = {
        "schema": "vibe-wrapper-trampoline/v1",
        "launch_mode": "canonical-entry",
        "host_id": str(contract.get("host_id") or (host_id or "").strip().lower()),
        "entry_id": entry.id,
        "requested_stage_stop": stop_stage,
        "allow_public_grade_flags": bool(entry.allow_grade_flags),
        "canonical_runtime_skill": "vibe",
        "entry_mode": str(contract.get("entry_mode") or ""),
        "launcher_kind": str(contract.get("launcher_kind") or ""),
        "fallback_policy": str(contract.get("fallback_policy") or ""),
        "proof_required": bool(contract.get("proof_required", True)),
    }
    trampoline_json = json.dumps(trampoline_payload, ensure_ascii=False, indent=2)
    return [
        "Canonical runtime trampoline contract (installer-managed wrapper):",
        "```json",
        trampoline_json,
        "```",
        "",
        f"Wrapper entry: {entry.display_name} (`{entry.id}`)",
        f"Default stop target: `{stop_stage}`",
        f"Public grade flags allowed: {grade_line}",
        bounded_warning,
        "Dispatch through canonical-entry runtime bridge. Do not treat this file as ordinary SKILL.md prose.",
        "If canonical runtime cannot be launched, report blocked instead of silently falling back.",
        "",
        "Request:",
        "$ARGUMENTS",
    ]


def build_wrapper_descriptors(host_id: str, surface: DiscoverableEntrySurface) -> dict[str, WrapperDescriptor]:
    contract = _wrapper_contract(host_id)
    descriptors: dict[str, WrapperDescriptor] = {}
    for entry in surface.entries:
        relpath = _host_wrapper_relpath(host_id, entry)
        content = "\n".join(
            [
                *_frontmatter_lines(host_id, entry, relpath=relpath),
                "",
                *_body_lines(host_id, entry, contract=contract),
                "",
            ]
        ) + "\n"
        descriptors[entry.id] = WrapperDescriptor(
            entry_id=entry.id,
            relpath=relpath,
            content=content,
        )
    return descriptors


def _host_surface_targets(host_id: str, descriptor: WrapperDescriptor) -> tuple[Path, ...]:
    normalized = (host_id or "").strip().lower()
    if normalized == "opencode" and descriptor.relpath.parts and descriptor.relpath.parts[0] == "commands":
        return (
            descriptor.relpath,
            Path("command") / descriptor.relpath.name,
        )
    return (descriptor.relpath,)


def materialize_host_visible_wrappers(
    *,
    target_root: Path,
    host_id: str,
    surface: DiscoverableEntrySurface,
) -> list[Path]:
    descriptors = build_wrapper_descriptors(host_id, surface)
    written: list[Path] = []
    for descriptor in descriptors.values():
        for destination_rel in _host_surface_targets(host_id, descriptor):
            destination = target_root / destination_rel
            if descriptor.entry_id == "vibe" and destination_rel == Path("skills") / "vibe" / "SKILL.md" and destination.exists():
                written.append(destination)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(descriptor.content, encoding="utf-8")
            written.append(destination)
    return written
