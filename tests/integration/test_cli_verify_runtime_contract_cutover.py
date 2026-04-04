from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cli_verify_entrypoint_uses_runtime_contract_owner() -> None:
    main = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "main.py").read_text(encoding="utf-8")
    commands = (REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli" / "commands.py").read_text(encoding="utf-8")

    assert "verify_command" in main
    assert "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1" not in main
    assert "from .repo import get_installed_runtime_config" in commands
    assert "def verify_command(" in commands
    assert "runtime_cfg['coherence_gate']" in commands
