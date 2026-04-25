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
    if entry.id == "vibe-upgrade":
        return Path("skills") / entry.id / "SKILL.md"
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
    return resolve_canonical_vibe_contract(None, normalized)


def _body_lines(host_id: str, entry: DiscoverableEntry, *, contract: dict[str, object]) -> list[str]:
    if entry.id == "vibe-upgrade":
        normalized_host_id = str(contract.get("host_id") or (host_id or "").strip().lower())
        upgrade_payload = {
            "schema": "vibe-upgrade-skill/v1",
            "entry_id": entry.id,
            "operation": "upgrade_current_host_installation",
            "host_id": normalized_host_id,
            "backend": "vgo-cli upgrade",
            "official_default_branch_only": True,
            "bypass_vibe_router": True,
        }
        upgrade_json = json.dumps(upgrade_payload, ensure_ascii=False, indent=2)
        return [
            "Installer-managed upgrade skill contract:",
            "```json",
            upgrade_json,
            "```",
            "",
            f"Wrapper entry: {entry.display_name} (`{entry.id}`)",
            "This is an upgrade operation, not a normal staged `vibe` task.",
            "Do not run the router for this entry.",
            "Do not relaunch this request as `entry_id = vibe`.",
            "Do not freeze a requirement document or execution plan for this entry.",
            "Do not invoke TDD, specialist dispatch, or delivery-acceptance gates for this entry unless the upgrade backend itself reports a verification failure.",
            "Run the shared upgrade backend for the current host installation, then verify and report the before/after install state.",
            "Use the installed runtime root as `--repo-root`; the backend will resolve or prepare the official default-branch source checkout when needed.",
            "",
            "PowerShell execution shape:",
            "```powershell",
            "# Set this to the host root that contains skills\\vibe-upgrade\\SKILL.md.",
            "$targetRoot = '<host-root>'",
            "$repoRoot = Join-Path $targetRoot 'skills\\vibe'",
            "$env:PYTHONPATH = Join-Path $repoRoot 'apps\\vgo-cli\\src'",
            f"py -3 -m vgo_cli.main upgrade --repo-root $repoRoot --host {normalized_host_id} --target-root $targetRoot --frontend powershell --profile full",
            "```",
            "",
            "If the request is empty, default to upgrading the current host installation through shared `vgo-cli upgrade` and verify the result.",
            "If the backend fails, report the exact backend error and do not fall back to ordinary `vibe` routing.",
            "",
            "Request:",
            "$ARGUMENTS",
        ]

    grade_line = "yes" if entry.allow_grade_flags else "no"
    stop_stage = entry.requested_stage_stop
    progressive_stop_sequence = [stage for stage in entry.progressive_stage_stops if stage]
    if progressive_stop_sequence:
        bounded_warning = (
            "Canonical `vibe` progresses through governed approval boundaries and may stop early even though the full "
            "runtime still owns `phase_cleanup`."
        )
    else:
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
    if progressive_stop_sequence:
        trampoline_payload["progressive_stage_stops"] = progressive_stop_sequence
    if entry.id in {"vibe-how-do-we-do", "vibe-do-it"}:
        trampoline_payload["bounded_reentry_credentials"] = {
            "runtime_summary_field": "bounded_return_control",
            "required": True,
            "required_cli_flags": ["--continue-from-run-id", "--bounded-reentry-token"],
        }
    trampoline_json = json.dumps(trampoline_payload, ensure_ascii=False, indent=2)
    empty_request_line = (
        "If the request is empty, default to upgrading the current host installation through shared `vgo-cli upgrade` and verify the result."
        if entry.id == "vibe-upgrade"
        else None
    )
    continuation_lines = []
    if entry.id == "vibe":
        continuation_lines = [
            "If the latest verified runtime summary exposes `bounded_return_control.explicit_user_reentry_required = true`, return control to the user immediately.",
            "Do not consume `--continue-from-run-id` and `--bounded-reentry-token` in the same assistant turn that produced the bounded stop.",
            "Wait for a new user message that explicitly approves or revises the frozen requirement/plan, then re-enter canonical `vibe` and forward those credentials automatically from the latest bounded summary.",
            "Treat the runtime summary's `terminal_stage`, `next_stage`, and `approval_prompt` as the authoritative boundary contract instead of guessing whether planning/execution should continue.",
        ]
    elif entry.id in {"vibe-how-do-we-do", "vibe-do-it"}:
        continuation_lines = [
            "If this wrapper continues a prior canonical run in the same thread or workspace, reuse the latest verified frozen requirement/plan as continuation context.",
            "If the latest verified runtime summary exposes `bounded_return_control.explicit_user_reentry_required = true`, do not continue on prose alone.",
            "Forward `--continue-from-run-id <source_run_id>` and `--bounded-reentry-token <reentry_token>` from that latest bounded summary before launching the next wrapper.",
            "Without those credentials, treat the follow-up as blocked instead of auto-continuing later stages.",
            "When extracting keyword intent for the router, include the frozen goal, deliverable, constraints, and capability hints from the earlier governed artifacts instead of reducing the request to a bare `execute plan` summary.",
            "Do not reopen generic clarification questions unless the user changed scope or the prior governed artifacts are missing or stale.",
        ]
    post_launch_lines = [
        "After proof validation, read the returned session root's user-facing outputs before you answer. At minimum inspect `host-user-briefing.md`; if present, also inspect `delivery-acceptance-report.json` and `runtime-summary.json`.",
        "Treat canonical proof artifacts as launch/authenticity evidence only; they are not by themselves proof that downstream execution or specialist work already finished.",
    ]
    if stop_stage == "phase_cleanup":
        post_launch_lines.extend(
            [
                "If `delivery-acceptance-report.json` exists and reports `completion_language_allowed = false` or a non-`fully_ready` readiness state, do not describe the run as completed successfully; report the pending/manual-review state and the blocking truth layers instead.",
                "If `host-user-briefing.md` reports `routed_pending_current_session`, or if the session artifacts show `execution_driver = direct_current_session_route` / `live_native_execution = false` for approved execution skills, continue by loading those disclosed skill entrypoints in the current host session instead of stopping at proof validation.",
            ]
        )
    return [
        "Canonical runtime trampoline contract (installer-managed wrapper):",
        "```json",
        trampoline_json,
        "```",
        "",
        f"Wrapper entry: {entry.display_name} (`{entry.id}`)",
        f"Default stop target: `{stop_stage}`",
        *(
            [f"Progressive stop sequence: `{ '`, `'.join(progressive_stop_sequence) }`"]
            if progressive_stop_sequence
            else []
        ),
        f"Public grade flags allowed: {grade_line}",
        bounded_warning,
        "Wrapper labels only select the bounded terminal stage. Canonical `vibe` still owns router selection, `confirm_required`, and runtime authority.",
        "Dispatch through canonical-entry runtime bridge. Do not treat this file as ordinary SKILL.md prose.",
        "Launch canonical-entry first. Do not preflight-scan the current workspace or repository for canonical proof files before launch.",
        "If canonical-entry returns a session root, validate canonical proof artifacts only inside that launched session root.",
        *post_launch_lines,
        "If canonical runtime cannot be launched, report blocked instead of silently falling back.",
        *continuation_lines,
        *([empty_request_line] if empty_request_line else []),
        "",
        "Request:",
        "$ARGUMENTS",
    ]


def build_wrapper_descriptors(host_id: str, surface: DiscoverableEntrySurface) -> dict[str, WrapperDescriptor]:
    contract = _wrapper_contract(host_id)
    descriptors: dict[str, WrapperDescriptor] = {}
    for entry in surface.public_entries:
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
