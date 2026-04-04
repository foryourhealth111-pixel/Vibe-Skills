from __future__ import annotations

from pathlib import Path
from typing import Any

from .policies import enforce_execution_context, file_parity, relative_file_list
from .runtime_freshness_support import (
    FreshnessEvaluationContext,
    build_freshness_artifact,
    build_freshness_results,
)


def _log_assertion(assertions: list[bool], condition: bool, message: str) -> None:
    prefix = '[PASS]' if condition else '[FAIL]'
    print(f'{prefix} {message}')
    assertions.append(condition)


def _evaluate_mirrored_files(
    context: FreshnessEvaluationContext,
    results: dict[str, Any],
    assertions: list[bool],
) -> None:
    for rel in context.packaging['mirror']['files']:
        canonical_path = (context.canonical_root / rel).resolve()
        installed_path = (context.installed_root / rel).resolve()
        canonical_exists = canonical_path.exists()
        installed_exists = installed_path.exists()
        parity = canonical_exists and installed_exists and file_parity(canonical_path, installed_path, context.ignore_keys)
        _log_assertion(assertions, canonical_exists, f'[file:{rel}] canonical exists')
        _log_assertion(assertions, installed_exists, f'[file:{rel}] installed exists')
        if canonical_exists and installed_exists:
            _log_assertion(assertions, parity, f'[file:{rel}] parity')
        results['files'].append(
            {
                'path': rel,
                'canonical_exists': canonical_exists,
                'installed_exists': installed_exists,
                'parity': parity,
            }
        )


def _evaluate_mirrored_directories(
    context: FreshnessEvaluationContext,
    results: dict[str, Any],
    assertions: list[bool],
) -> None:
    for rel in context.packaging['mirror']['directories']:
        canonical_dir = (context.canonical_root / rel).resolve()
        installed_dir = (context.installed_root / rel).resolve()
        canonical_exists = canonical_dir.exists()
        installed_exists = installed_dir.exists()
        _log_assertion(assertions, canonical_exists, f'[dir:{rel}] canonical exists')
        _log_assertion(assertions, installed_exists, f'[dir:{rel}] installed exists')

        only_main: list[str] = []
        only_installed: list[str] = []
        diff_files: list[str] = []
        if canonical_exists and installed_exists:
            canonical_files = relative_file_list(canonical_dir)
            installed_files = relative_file_list(installed_dir)
            installed_set = set(installed_files)
            canonical_set = set(canonical_files)
            only_main = sorted(canonical_set - installed_set)
            only_installed = sorted(
                path
                for path in installed_set - canonical_set
                if f'{rel}/{path}' not in context.allow_installed_only
            )
            for file_rel in sorted(canonical_set & installed_set):
                if not file_parity(canonical_dir / file_rel, installed_dir / file_rel, context.ignore_keys):
                    diff_files.append(file_rel)

        _log_assertion(assertions, len(only_main) == 0, f'[dir:{rel}] no files missing in installed runtime')
        _log_assertion(assertions, len(only_installed) == 0, f'[dir:{rel}] no unexpected installed-only files')
        _log_assertion(assertions, len(diff_files) == 0, f'[dir:{rel}] file parity')
        results['directories'].append(
            {
                'path': rel,
                'only_in_canonical': only_main,
                'only_in_installed': only_installed,
                'diff_files': diff_files,
            }
        )


def _evaluate_runtime_markers(
    context: FreshnessEvaluationContext,
    results: dict[str, Any],
    assertions: list[bool],
) -> None:
    for rel in context.runtime['required_runtime_markers']:
        canonical_path = (context.canonical_root / rel).resolve()
        installed_path = (context.installed_root / rel).resolve()
        canonical_exists = canonical_path.exists()
        installed_exists = installed_path.exists()
        parity = canonical_exists and installed_exists and file_parity(canonical_path, installed_path, context.ignore_keys)
        _log_assertion(assertions, canonical_exists, f'[marker:{rel}] canonical exists')
        _log_assertion(assertions, installed_exists, f'[marker:{rel}] installed exists')
        if canonical_exists and installed_exists:
            _log_assertion(assertions, parity, f'[marker:{rel}] parity')
        results['runtime_markers'].append(
            {
                'path': rel,
                'canonical_exists': canonical_exists,
                'installed_exists': installed_exists,
                'parity': parity,
            }
        )


def evaluate_freshness_runtime(
    context: FreshnessEvaluationContext,
    script_path: Path,
) -> tuple[bool, dict[str, Any]]:
    enforce_execution_context(context.governance_context, script_path)
    results = build_freshness_results(context)
    assertions: list[bool] = []

    print('=== VCO Installed Runtime Freshness Gate ===')
    print(f'Repo root    : {context.repo_root}')
    print(f'Target root  : {context.target_root}')
    print(f'Installed root: {context.installed_root}')

    installed_exists = context.installed_root.exists()
    _log_assertion(assertions, installed_exists, '[runtime] installed vibe root exists')
    if context.runtime.get('require_nested_bundled_root'):
        _log_assertion(assertions, context.nested_root.exists(), '[runtime] nested bundled root exists')

    _evaluate_mirrored_files(context, results, assertions)
    _evaluate_mirrored_directories(context, results, assertions)
    _evaluate_runtime_markers(context, results, assertions)

    total = len(assertions)
    passed = sum(1 for assertion in assertions if assertion)
    failed = total - passed
    gate_pass = failed == 0

    print()
    print('=== Summary ===')
    print(f'Total assertions: {total}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f"Gate Result: {'PASS' if gate_pass else 'FAIL'}")

    return gate_pass, build_freshness_artifact(gate_pass, results, total, passed, failed)
