from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_registry_query_exposes_bootstrap_host_catalog() -> None:
    supported = subprocess.run(
        ['python3', 'scripts/common/adapter_registry_query.py', '--repo-root', '.', '--supported-hosts'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    choices = subprocess.run(
        ['python3', 'scripts/common/adapter_registry_query.py', '--repo-root', '.', '--bootstrap-choice-lines'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert supported.stdout.strip() == 'codex|claude-code|cursor|windsurf|openclaw|opencode'
    assert '1	codex	strongest governed lane	codex' in choices.stdout
    assert '2	claude-code	supported install/use path	claude-code,claude' in choices.stdout
    assert '6	opencode	preview guidance adapter	opencode' in choices.stdout


def test_powershell_governance_helpers_expose_bootstrap_host_catalog() -> None:
    command = (
        ". ./scripts/common/vibe-governance-helpers.ps1; "
        "$choices = @(Get-VgoBootstrapHostChoices -StartPath .); "
        "$hint = Get-VgoSupportedHostHint -StartPath .; "
        "Write-Output $hint; "
        "Write-Output ($choices[1].aliases -join ',')"
    )
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-Command', command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines[0] == 'codex|claude-code|cursor|windsurf|openclaw|opencode'
    assert lines[1] == 'claude-code,claude'
