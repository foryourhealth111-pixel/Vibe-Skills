from __future__ import annotations

from pathlib import Path

from .errors import CliError
from .workspace import extend_workspace_package_path


def refresh_install_ledger_payload(repo_root: Path, target_root: Path) -> dict[str, object]:
    extend_workspace_package_path(repo_root)
    from vgo_installer.ledger_service import refresh_install_ledger
    from vgo_verify.bootstrap_doctor_runtime import collect_host_runtime

    try:
        payload = refresh_install_ledger(target_root)
    except SystemExit as exc:
        raise CliError(str(exc)) from exc
    payload['host_runtime'] = collect_host_runtime(target_root)
    return payload
