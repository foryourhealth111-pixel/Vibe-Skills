from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .policies import (
    GovernanceContext,
    mirror_topology_targets,
    resolve_packaging_contract,
    utc_now,
    write_text,
)


@dataclass(slots=True)
class FreshnessEvaluationContext:
    repo_root: Path
    governance: dict[str, Any]
    canonical_root: Path
    target_root: Path
    governance_context: GovernanceContext
    packaging: dict[str, Any]
    runtime: dict[str, Any]
    ignore_keys: set[str]
    installed_root: Path
    receipt_path: Path
    allow_installed_only: set[str]
    nested_root: Path


def build_freshness_context(
    repo_root: Path,
    governance: dict[str, Any],
    canonical_root: Path,
    target_root: Path,
    runtime: dict[str, Any],
) -> FreshnessEvaluationContext:
    packaging = resolve_packaging_contract(governance, repo_root)
    governance_context = GovernanceContext(
        repo_root=repo_root,
        governance_path=repo_root / 'config' / 'version-governance.json',
        governance=governance,
        canonical_root=canonical_root,
        packaging=packaging,
        runtime_config=runtime,
        mirror_targets=mirror_topology_targets(governance, repo_root),
    )
    ignore_keys = set(packaging['normalized_json_ignore_keys'])
    installed_root = (target_root / runtime['target_relpath']).resolve()
    receipt_path = (target_root / runtime['receipt_relpath']).resolve()
    allow_installed_only = set(packaging.get('allow_installed_only') or packaging['allow_bundled_only'])
    generated = (governance.get('packaging') or {}).get('generated_compatibility') or {}
    nested_runtime = generated.get('nested_runtime_root') or {}
    nested_rel = str(nested_runtime.get('relative_path') or 'bundled/skills/vibe').strip()
    nested_root = (installed_root / nested_rel).resolve()
    return FreshnessEvaluationContext(
        repo_root=repo_root,
        governance=governance,
        canonical_root=canonical_root,
        target_root=target_root,
        governance_context=governance_context,
        packaging=packaging,
        runtime=runtime,
        ignore_keys=ignore_keys,
        installed_root=installed_root,
        receipt_path=receipt_path,
        allow_installed_only=allow_installed_only,
        nested_root=nested_root,
    )


def build_freshness_results(context: FreshnessEvaluationContext) -> dict[str, Any]:
    return {
        'target_root': str(context.target_root.resolve()),
        'installed_root': str(context.installed_root),
        'receipt_path': str(context.receipt_path),
        'release': {
            'version': str((context.governance.get('release') or {}).get('version') or ''),
            'updated': str((context.governance.get('release') or {}).get('updated') or ''),
        },
        'files': [],
        'directories': [],
        'runtime_markers': [],
        'nested': {
            'required': bool(context.runtime.get('require_nested_bundled_root')),
            'path': str(context.nested_root),
            'exists': context.nested_root.exists(),
        },
    }


def build_freshness_artifact(
    gate_pass: bool,
    results: dict[str, Any],
    total: int,
    passed: int,
    failed: int,
) -> dict[str, Any]:
    return {
        'generated_at': utc_now(),
        'gate_result': 'PASS' if gate_pass else 'FAIL',
        'assertions': {
            'total': total,
            'passed': passed,
            'failed': failed,
        },
        'results': results,
    }


def write_freshness_artifacts(repo_root: Path, artifact: dict[str, Any]) -> None:
    output_dir = repo_root / 'outputs' / 'verify'
    write_text(
        output_dir / 'vibe-installed-runtime-freshness-gate.json',
        json.dumps(artifact, ensure_ascii=False, indent=2) + '\n',
    )
    results = artifact['results']
    markdown = '\n'.join(
        [
            '# VCO Installed Runtime Freshness Gate',
            '',
            f"- Gate Result: **{artifact['gate_result']}**",
            f"- Assertions: total={artifact['assertions']['total']}, passed={artifact['assertions']['passed']}, failed={artifact['assertions']['failed']}",
            f"- Target root: `{results['target_root']}`",
            f"- Installed root: `{results['installed_root']}`",
            f"- release.version: `{results['release']['version']}`",
            f"- release.updated: `{results['release']['updated']}`",
        ]
    )
    write_text(output_dir / 'vibe-installed-runtime-freshness-gate.md', markdown + '\n')


def write_freshness_receipt(context: FreshnessEvaluationContext, gate_pass: bool, artifact: dict[str, Any]) -> None:
    if gate_pass:
        receipt = {
            'generated_at': utc_now(),
            'gate_result': 'PASS',
            'release': artifact['results']['release'],
            'target_root': str(context.target_root.resolve()),
            'installed_root': str(context.installed_root),
            'receipt_version': int(context.runtime.get('receipt_contract_version', 1)),
        }
        write_text(context.receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    elif context.receipt_path.exists():
        context.receipt_path.unlink()
