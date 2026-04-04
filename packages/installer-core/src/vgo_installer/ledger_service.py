from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from vgo_contracts.install_ledger import InstallLedger

from ._io import load_json, write_json_file

if TYPE_CHECKING:
    from .install_plan import InstallPlan


@dataclass(slots=True)
class MaterializationLedgerState:
    created_paths: set[Path | str] = field(default_factory=set)
    owned_tree_roots: set[Path | str] = field(default_factory=set)
    managed_json_paths: set[Path | str] = field(default_factory=set)
    merged_files: dict[str, dict[str, object]] = field(default_factory=dict)
    generated_from_template_if_absent: set[Path | str] = field(default_factory=set)
    specialist_wrapper_paths: list[Path | str] = field(default_factory=list)


def _normalize_resolved_path(path: Path | str) -> str:
    return str(Path(path).resolve(strict=False))


def _normalize_skill_name(value: object) -> str | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        InstallLedger(managed_skill_names=[text])
    except ValueError:
        return None
    return text


def sanitize_managed_skill_names(values: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    safe_names: set[str] = set()
    for value in values or []:
        normalized = _normalize_skill_name(value)
        if normalized is not None:
            safe_names.add(normalized)
    return sorted(safe_names)


def load_existing_install_ledger(target_root: Path | str) -> dict | None:
    ledger_path = Path(target_root).resolve() / '.vibeskills' / 'install-ledger.json'
    if not ledger_path.exists():
        return None
    return load_json(ledger_path)


def derive_managed_skill_names_from_ledger(target_root: Path | str, ledger: dict | None) -> set[str]:
    if not isinstance(ledger, dict):
        return set()

    target_root_path = Path(target_root).resolve()
    managed = set(sanitize_managed_skill_names(ledger.get('managed_skill_names')))
    skills_root = (target_root_path / 'skills').resolve(strict=False)

    for raw_path in ledger.get('created_paths') or []:
        candidate = Path(str(raw_path)).resolve(strict=False)
        try:
            relative = candidate.relative_to(skills_root)
        except ValueError:
            continue
        if relative.parts:
            normalized = _normalize_skill_name(relative.parts[0])
            if normalized is not None:
                managed.add(normalized)

    canonical_vibe_root = str(ledger.get('canonical_vibe_root') or '').strip()
    if canonical_vibe_root:
        normalized = _normalize_skill_name(Path(canonical_vibe_root).name)
        if normalized is not None:
            managed.add(normalized)

    return managed


def build_payload_summary(target_root: Path | str, ledger: dict) -> dict[str, object]:
    target_root_path = Path(target_root).resolve()
    target_root_resolved = target_root_path.resolve(strict=False)
    managed_skill_names = derive_managed_skill_names_from_ledger(target_root_path, ledger)
    installed_skill_names = sorted(
        name
        for name in managed_skill_names
        if not name.startswith('.') and (target_root_path / 'skills' / name).is_dir()
    )

    managed_skill_roots = {
        (target_root_path / 'skills' / name).resolve(strict=False)
        for name in managed_skill_names
        if (target_root_path / 'skills' / name).exists()
    }

    owned_files: set[str] = set()

    def is_under_target_root(candidate: Path) -> bool:
        try:
            candidate.relative_to(target_root_resolved)
        except ValueError:
            return False
        return True

    def collect_owned_tree(path_value: Path | str) -> None:
        candidate = Path(path_value).resolve(strict=False)
        if not is_under_target_root(candidate) or not candidate.is_dir():
            return
        for file_path in candidate.rglob('*'):
            if file_path.is_file():
                owned_files.add(str(file_path.resolve(strict=False)))

    def collect_owned_file(path_value: Path | str) -> None:
        candidate = Path(path_value).resolve(strict=False)
        if not is_under_target_root(candidate) or not candidate.is_file():
            return
        owned_files.add(str(candidate))

    for skill_root in managed_skill_roots:
        collect_owned_tree(skill_root)

    skills_root = (target_root_path / 'skills').resolve(strict=False)
    for raw_path in ledger.get('owned_tree_roots') or []:
        candidate = Path(str(raw_path)).resolve(strict=False)
        if candidate == target_root_resolved or candidate == skills_root:
            continue
        if candidate.parent == skills_root and candidate.name not in managed_skill_names:
            continue
        collect_owned_tree(candidate)

    for raw_path in ledger.get('created_paths') or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get('managed_json_paths') or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get('generated_from_template_if_absent') or []:
        collect_owned_file(raw_path)
    for raw_path in ledger.get('specialist_wrapper_paths') or []:
        collect_owned_file(raw_path)
    for entry in ledger.get('merged_files') or []:
        if isinstance(entry, dict):
            collect_owned_file(str(entry.get('path') or ''))

    return {
        'installed_skill_count': len(installed_skill_names),
        'installed_skill_names': installed_skill_names,
        'installed_file_count': len(owned_files),
    }


def _sorted_paths(values: set[Path | str]) -> list[str]:
    return sorted(_normalize_resolved_path(value) for value in values)


def _sorted_merged_files(values: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for key in sorted(values):
        entry = dict(values[key])
        entry['path'] = _normalize_resolved_path(entry.get('path') or key)
        entry['created_if_absent'] = bool(entry.get('created_if_absent'))
        records.append(entry)
    return records


def _sorted_wrapper_paths(values: list[Path | str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_resolved_path(value)
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def build_install_ledger(
    plan: 'InstallPlan',
    state: MaterializationLedgerState,
    *,
    external_fallback_used: list[str] | None = None,
    timestamp: str,
) -> dict[str, object]:
    ledger = {
        'schema_version': 1,
        'host_id': plan.host_id,
        'install_mode': plan.install_mode,
        'profile': plan.profile,
        'target_root': str(plan.target_root),
        'runtime_root': str(plan.runtime_root),
        'canonical_vibe_root': str((plan.target_root / plan.canonical_vibe_rel).resolve(strict=False)),
        'created_paths': _sorted_paths(state.created_paths),
        'owned_tree_roots': _sorted_paths(state.owned_tree_roots),
        'managed_json_paths': _sorted_paths(state.managed_json_paths),
        'merged_files': _sorted_merged_files(state.merged_files),
        'generated_from_template_if_absent': _sorted_paths(state.generated_from_template_if_absent),
        'specialist_wrapper_paths': _sorted_wrapper_paths(state.specialist_wrapper_paths),
        'external_fallback_used': list(external_fallback_used or []),
        'managed_skill_names': list(plan.managed_skill_names),
        'packaging_manifest': dict(plan.packaging_manifest),
        'timestamp': timestamp,
        'ownership_source': 'install-ledger',
    }
    ledger['payload_summary'] = build_payload_summary(plan.target_root, ledger)
    return ledger


def write_install_ledger(
    plan: 'InstallPlan',
    state: MaterializationLedgerState,
    *,
    external_fallback_used: list[str] | None = None,
    timestamp: str,
) -> Path:
    ledger_path = plan.target_root / '.vibeskills' / 'install-ledger.json'
    ledger = build_install_ledger(
        plan,
        state,
        external_fallback_used=external_fallback_used,
        timestamp=timestamp,
    )
    write_json_file(ledger_path, ledger)
    return ledger_path


def refresh_install_ledger(target_root: Path | str) -> dict[str, object]:
    target_root_path = Path(target_root).resolve()
    ledger_path = target_root_path / '.vibeskills' / 'install-ledger.json'
    if not ledger_path.exists():
        raise SystemExit(f'Install ledger missing for refresh: {ledger_path}')

    ledger = load_json(ledger_path)
    ledger['payload_summary'] = build_payload_summary(target_root_path, ledger)
    write_json_file(ledger_path, ledger)
    return {
        'ledger_path': str(ledger_path.resolve()),
        'payload_summary': ledger['payload_summary'],
    }
