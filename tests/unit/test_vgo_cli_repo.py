from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.repo import get_installed_runtime_config, resolve_canonical_repo_root


def test_get_installed_runtime_config_merges_defaults_with_governance_overrides(tmp_path: Path) -> None:
    repo_root = tmp_path / 'repo'
    (repo_root / 'config').mkdir(parents=True)
    (repo_root / 'config' / 'version-governance.json').write_text(
        '{"runtime": {"installed_runtime": {"post_install_gate": "scripts/verify/custom-gate.ps1"}}}',
        encoding='utf-8',
    )

    payload = get_installed_runtime_config(repo_root)

    assert payload['post_install_gate'] == 'scripts/verify/custom-gate.ps1'
    assert payload['receipt_relpath'] == 'skills/vibe/outputs/runtime-freshness-receipt.json'
    assert payload['frontmatter_gate'] == 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
    assert payload['coherence_gate'] == 'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
    assert payload['runtime_entrypoint'] == 'scripts/runtime/invoke-vibe-runtime.ps1'


def test_resolve_canonical_repo_root_prefers_outer_git_root_with_governance(tmp_path: Path) -> None:
    repo_root = tmp_path / 'outer'
    nested = repo_root / 'apps' / 'vgo-cli' / 'src'
    nested.mkdir(parents=True)
    (repo_root / '.git').mkdir()
    (repo_root / 'config').mkdir()
    (repo_root / 'config' / 'version-governance.json').write_text('{}', encoding='utf-8')

    assert resolve_canonical_repo_root(nested) == repo_root
    assert resolve_canonical_repo_root(tmp_path) is None
