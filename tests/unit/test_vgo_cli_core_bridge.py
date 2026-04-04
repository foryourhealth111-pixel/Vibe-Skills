from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import types

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

import vgo_cli.core_bridge as core_bridge


@pytest.mark.parametrize(
    ('function_name', 'package_name', 'module_name'),
    [
        ('run_installer_core', 'vgo_installer', 'vgo_installer.install_runtime'),
        ('run_uninstaller_core', 'vgo_installer', 'vgo_installer.uninstall_runtime'),
        ('run_router_core', 'vgo_runtime', 'vgo_runtime.router_bridge'),
    ],
)
def test_core_bridge_extends_workspace_and_invokes_selected_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    function_name: str,
    package_name: str,
    module_name: str,
) -> None:
    recorded: dict[str, object] = {}

    def fake_extend(repo_root: Path) -> None:
        recorded['repo_root'] = repo_root

    def fake_invoke(main_fn, argv):
        recorded['main_fn'] = main_fn
        recorded['argv'] = list(argv)
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout='', stderr='')

    def fake_main(argv: list[str] | None = None) -> int:
        return 0

    pkg = types.ModuleType(package_name)
    pkg.__path__ = []
    module = types.ModuleType(module_name)
    module.main = fake_main

    monkeypatch.setattr(core_bridge, 'extend_workspace_package_path', fake_extend)
    monkeypatch.setattr(core_bridge, 'invoke_python_core', fake_invoke)
    monkeypatch.setitem(sys.modules, package_name, pkg)
    monkeypatch.setitem(sys.modules, module_name, module)

    result = getattr(core_bridge, function_name)(tmp_path, ['--flag'])

    assert result.returncode == 0
    assert recorded['repo_root'] == tmp_path
    assert recorded['main_fn'] is fake_main
    assert recorded['argv'] == ['--flag']
