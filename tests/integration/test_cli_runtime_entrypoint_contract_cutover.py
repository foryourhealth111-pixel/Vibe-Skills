from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cli_runtime_entrypoint_uses_runtime_contract_owner() -> None:
    main = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "main.py").read_text(encoding="utf-8")
    commands = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "commands.py").read_text(encoding="utf-8")
    contract = (REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "installed_runtime_contract.py").read_text(encoding="utf-8")

    assert "runtime_command" in main
    assert "scripts/runtime/invoke-vibe-runtime.ps1" not in main
    assert "from .repo import get_installed_runtime_config" in commands
    assert "def runtime_command(" in commands
    assert "runtime_cfg['runtime_entrypoint']" in commands
    assert "DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT" in contract
