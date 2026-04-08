from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vgo_contracts.discoverable_entry_surface import DiscoverableEntry, DiscoverableEntrySurface
from vgo_contracts.runtime_surface_contract import uses_skill_only_activation


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


def _body_lines(entry: DiscoverableEntry) -> list[str]:
    grade_line = "yes" if entry.allow_grade_flags else "no"
    stop_stage = entry.requested_stage_stop
    bounded_warning = (
        f"Stop at `{stop_stage}` and re-enter through canonical `vibe` or another approved wrapper to continue later stages."
        if stop_stage != "phase_cleanup"
        else "Continue through `phase_cleanup` without creating a second runtime authority."
    )
    return [
        "Use the `vibe` skill and follow its governed runtime contract for this request.",
        "",
        f"Wrapper entry: {entry.display_name} (`{entry.id}`)",
        f"Default stop target: `{stop_stage}`",
        f"Public grade flags allowed: {grade_line}",
        bounded_warning,
        "",
        "Request:",
        "$ARGUMENTS",
    ]


def build_wrapper_descriptors(host_id: str, surface: DiscoverableEntrySurface) -> dict[str, WrapperDescriptor]:
    descriptors: dict[str, WrapperDescriptor] = {}
    for entry in surface.entries:
        relpath = _host_wrapper_relpath(host_id, entry)
        content = "\n".join([*_frontmatter_lines(host_id, entry, relpath=relpath), "", *_body_lines(entry), ""]) + "\n"
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
