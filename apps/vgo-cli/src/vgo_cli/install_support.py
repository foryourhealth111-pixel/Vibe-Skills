from __future__ import annotations

from pathlib import Path

from .external import report_external_fallback_usage
from .install_gates import run_offline_gate, run_runtime_freshness_gate
from .installer_bridge import refresh_install_ledger_payload
from .output import print_json_payload
from .skill_surface import quarantine_codex_duplicate_skill_surface


def reconcile_install_postconditions(
    repo_root: Path,
    target_root: Path,
    host_id: str,
    *,
    external_fallback_used: list[str],
    strict_offline: bool,
    skip_runtime_freshness_gate: bool,
    include_frontmatter: bool,
) -> None:
    if strict_offline:
        run_offline_gate(repo_root, target_root)
    report_external_fallback_usage(external_fallback_used, strict_offline=strict_offline)
    quarantine_codex_duplicate_skill_surface(target_root, host_id)
    run_runtime_freshness_gate(
        repo_root,
        target_root,
        skip_gate=skip_runtime_freshness_gate,
        include_frontmatter=include_frontmatter,
    )
    print_json_payload(refresh_install_ledger_payload(repo_root, target_root))
