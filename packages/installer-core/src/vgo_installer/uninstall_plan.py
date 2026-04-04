from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ledger_service import derive_managed_skill_names_from_ledger, load_existing_install_ledger


@dataclass(frozen=True, slots=True)
class UninstallPlan:
    host_id: str
    target_root: Path
    ledger_path: Path
    managed_skill_names: tuple[str, ...]


def build_uninstall_plan(target_root: Path | str) -> UninstallPlan:
    target_root_path = Path(target_root).resolve()
    ledger = load_existing_install_ledger(target_root_path)
    if ledger is None:
        raise SystemExit(f'Install ledger missing for uninstall: {target_root_path}')
    return UninstallPlan(
        host_id=str(ledger.get('host_id') or '').strip(),
        target_root=target_root_path,
        ledger_path=target_root_path / '.vibeskills' / 'install-ledger.json',
        managed_skill_names=tuple(sorted(derive_managed_skill_names_from_ledger(target_root_path, ledger))),
    )
