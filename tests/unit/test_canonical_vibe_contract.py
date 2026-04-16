from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
if str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.canonical_vibe_contract import (
    resolve_canonical_vibe_contract,
    uses_skill_only_activation,
)


def test_resolve_canonical_vibe_contract_projects_supported_hosts() -> None:
    assert resolve_canonical_vibe_contract(REPO_ROOT, "codex")["entry_mode"] == "direct_runtime"
    assert resolve_canonical_vibe_contract(REPO_ROOT, "claude-code")["entry_mode"] == "bridged_runtime"
    assert resolve_canonical_vibe_contract(REPO_ROOT, "opencode")["entry_mode"] == "bridged_runtime"


def test_supported_hosts_forbid_skill_doc_fallback() -> None:
    for host_id in ("codex", "claude-code", "opencode"):
        contract = resolve_canonical_vibe_contract(REPO_ROOT, host_id)
        assert contract["fallback_policy"] == "blocked"
        assert contract["allow_skill_doc_fallback"] is False
        assert contract["proof_required"] is True
        assert contract["supports_bounded_stop"] is True


def test_uses_skill_only_activation_resolves_from_adapter_registry_contract() -> None:
    assert uses_skill_only_activation("codex", start_path=REPO_ROOT) is False
    assert uses_skill_only_activation("claude-code", start_path=REPO_ROOT) is True
    assert uses_skill_only_activation("opencode", start_path=REPO_ROOT) is True
    assert uses_skill_only_activation("cursor", start_path=REPO_ROOT) is True
    assert uses_skill_only_activation("windsurf", start_path=REPO_ROOT) is True
    assert uses_skill_only_activation("openclaw", start_path=REPO_ROOT) is True
