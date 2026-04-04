from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Sequence

from .process import invoke_python_core
from .workspace import extend_workspace_package_path


def run_installer_core(repo_root: Path, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    extend_workspace_package_path(repo_root)
    from vgo_installer.install_runtime import main as installer_main

    return invoke_python_core(installer_main, list(argv))


def run_uninstaller_core(repo_root: Path, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    extend_workspace_package_path(repo_root)
    from vgo_installer.uninstall_runtime import main as uninstaller_main

    return invoke_python_core(uninstaller_main, list(argv))


def run_router_core(repo_root: Path, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    extend_workspace_package_path(repo_root)
    from vgo_runtime.router_bridge import main as router_main

    return invoke_python_core(router_main, list(argv))
