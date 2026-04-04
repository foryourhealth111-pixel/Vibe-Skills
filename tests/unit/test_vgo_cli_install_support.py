from __future__ import annotations

from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / 'apps' / 'vgo-cli' / 'src'
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from vgo_cli.errors import CliError
from vgo_cli.external import report_external_fallback_usage
from vgo_cli.skill_surface import is_vibe_skill_dir, resolve_codex_duplicate_skill_root


def test_report_external_fallback_usage_warns_when_not_strict(capsys: pytest.CaptureFixture[str]) -> None:
    report_external_fallback_usage(['beta', 'alpha', 'beta'], strict_offline=False)

    captured = capsys.readouterr()
    assert '[WARN] External fallback skills were used (non-reproducible install): alpha,beta' in captured.out


def test_report_external_fallback_usage_rejects_when_strict() -> None:
    with pytest.raises(CliError, match='StrictOffline rejected external fallback usage: alpha,beta'):
        report_external_fallback_usage(['beta', 'alpha', 'beta'], strict_offline=True)


def test_resolve_codex_duplicate_skill_root_only_applies_to_codex_home(tmp_path: Path) -> None:
    codex_root = tmp_path / '.codex'
    codex_root.mkdir()

    assert resolve_codex_duplicate_skill_root(codex_root, 'codex') == tmp_path / '.agents' / 'skills' / 'vibe'
    assert resolve_codex_duplicate_skill_root(tmp_path / '.cursor', 'codex') is None
    assert resolve_codex_duplicate_skill_root(codex_root, 'cursor') is None


def test_is_vibe_skill_dir_detects_vibe_frontmatter(tmp_path: Path) -> None:
    skill_root = tmp_path / 'vibe'
    skill_root.mkdir()
    (skill_root / 'SKILL.md').write_text('name: vibe\n', encoding='utf-8')

    assert is_vibe_skill_dir(skill_root) is True
    assert is_vibe_skill_dir(tmp_path / 'missing') is False
