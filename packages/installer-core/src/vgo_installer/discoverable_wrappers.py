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
    return resolve_canonical_vibe_contract(None, normalized)


def _body_lines(host_id: str, entry: DiscoverableEntry, *, contract: dict[str, object]) -> list[str]:
    normalized_host_id = str(contract.get("host_id") or (host_id or "").strip().lower())
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
    trampoline_json = json.dumps(trampoline_payload, ensure_ascii=False, indent=2)
    continuation_lines = []
    if entry.id == "vibe":
        continuation_lines = [
            "Pass the current user task verbatim on initial launch and every bounded re-entry; unrelated chat history may be excluded. Do not summarize, rewrite, or reduce it to keywords.",
            "If the latest verified runtime summary exposes `bounded_return_control.explicit_user_reentry_required = true`, return control to the user immediately.",
            "Do not consume `--continue-from-run-id` and `--bounded-reentry-token` in the same assistant turn that produced the bounded stop.",
            "Do not treat the original detailed user request as approval of the frozen requirement or plan.",
            "Do not perform equivalent manual planning, execution, workaround delivery, or final artifact delivery outside governed re-entry.",
            "Wait for a new user message that explicitly approves or revises the frozen requirement/plan, then re-enter canonical `vibe` and forward those credentials automatically from the latest bounded summary.",
            "Treat the runtime summary's `terminal_stage`, `next_stage`, and `approval_prompt` as the authoritative boundary contract instead of guessing whether planning/execution should continue.",
        ]
    post_launch_lines = [
        "After proof validation, read the returned session root's user-facing outputs before you answer. At minimum inspect `host-user-briefing.md`; if present, also inspect `delivery-acceptance-report.json` and `runtime-summary.json`.",
        "Treat canonical proof artifacts as launch/authenticity evidence only; they are not by themselves proof that downstream execution or specialist work already finished.",
    ]
    if stop_stage == "phase_cleanup":
        post_launch_lines.extend(
            [
                "If `delivery-acceptance-report.json` exists and reports `completion_language_allowed = false` or a non-`fully_ready` readiness state, do not describe the run as completed successfully; report the pending/manual-review state and the blocking truth layers instead.",
                "If `agent-execution-handoff.json` reports `agent_action_required`, execute its waves in the current Agent turn: open every listed skill entrypoint, complete the assigned module work, write the full `module-execution.json`, then run the handoff's `return_command`. Do not ask the user for another approval.",
            ]
        )
    claude_bash_lines: list[str] = []
    if normalized_host_id == "claude-code" and entry.id == "vibe":
        claude_bash_lines = [
            "",
            "Claude Code Bash-safe launch shape (prefer this over Bash-wrapped PowerShell):",
            "```bash",
            "# Set this to the installed Vibe runtime root.",
            "REPO_ROOT='<host-root>/skills/vibe'",
            "# Set this once to the governed workspace root; do not rely on later cwd changes.",
            'WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"',
            '# Set VIBE_TASK to the current user task verbatim; do not summarize it.',
            'PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main canonical-entry \\',
            '  --repo-root "$REPO_ROOT" \\',
            '  --artifact-root "$WORKSPACE_ROOT" \\',
            "  --host-id claude-code \\",
            "  --entry-id vibe \\",
            '  --prompt "$VIBE_TASK"',
            "```",
            "",
            "Claude Code Bash-safe bounded re-entry shape:",
            "```bash",
            "REPO_ROOT='<host-root>/skills/vibe'",
            "# Reuse the same governed workspace root from the original launch.",
            'WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"',
            '# Reuse the same current user task verbatim in VIBE_TASK.',
            'DECISION_JSON="$WORKSPACE_ROOT/.vibeskills/tmp/host-decision.json"',
            'mkdir -p "$(dirname "$DECISION_JSON")"',
            "cat > \"$DECISION_JSON\" <<'JSON'",
            "{",
            '  "decision_kind": "approval_response",',
            '  "decision_action": "approve_requirement",',
            '  "approval_decision": "approve"',
            "}",
            "JSON",
            "",
            'PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main canonical-entry \\',
            '  --repo-root "$REPO_ROOT" \\',
            '  --artifact-root "$WORKSPACE_ROOT" \\',
            "  --host-id claude-code \\",
            "  --entry-id vibe \\",
            '  --prompt "$VIBE_TASK" \\',
            '  --continue-from-run-id "<source_run_id>" \\',
            '  --bounded-reentry-token "<reentry_token>" \\',
            '  --host-decision-json-file "$DECISION_JSON"',
            "```",
            "",
            "For a host-inferred revision, keep the same re-entry command shape but write `decision_action` as `revise_requirement` or `revise_plan`, set `approval_decision` to `revise`, and include a non-empty `revision_delta`. Structured revision refreezes the same bounded stage; it does not advance like approval.",
            "",
            "Do not place JSON decisions inside a Bash-wrapped PowerShell command. Use `--host-decision-json-file` so quoting, Unicode paths, and re-entry tokens stay intact.",
        ]
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
        *claude_bash_lines,
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
