from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vibe_skill_frontloads_canonical_bootstrap_contract() -> None:
    content = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "## Canonical Bootstrap" in content
    assert content.index("## Canonical Bootstrap") < content.index("## Unified Runtime Contract")
    assert "py -3 -m vgo_cli.main canonical-entry" in content
    bootstrap = content.split("## Canonical Bootstrap", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"`py -3`[^\n]*`python`[^\n]*`python3`[^\n]*availability", bootstrap)
    assert "do not place `$env:PYTHONPATH=...` inside a double-quoted `-Command` string" in content
    assert "corrupt it to `:PYTHONPATH`" in content
    assert '--artifact-root "<workspace_root>"' in content
    assert "Do not manually create `outputs/runtime/vibe-sessions/<run-id>/`" in content
    assert "Do not use the Vibe installation root as the governed artifact root" in content
    assert "Do not search the current workspace, repository, or install root for canonical proof files before launch" in content
    assert "Only validate canonical proof artifacts after canonical-entry returns a `session_root`" in content
    assert re.search(r"`check`[^\n]*`installed locally`[^\n]*runtime coherence and delivery acceptance[^\n]*evidence", bootstrap)
    assert "Do not inspect the repo, protocol docs, or prior run outputs before canonical launch returns" in content
    assert "Do not simulate stages, claim canonical entry from reading this file or wrapper text" in content
    assert "Proof of canonical launch is post-launch and requires: `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json` under the returned `session_root`." in content
    assert "report `blocked` with the concrete failure reason" in content
    assert "`vibe` is a host-syntax-neutral skill contract." in content
    assert "public runtime entry" not in content
    assert "second public runtime skill" not in content
