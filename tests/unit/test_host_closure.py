from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for src in (ROOT / "packages" / "contracts" / "src", ROOT / "packages" / "installer-core" / "src"):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.host_closure import (
    install_claude_managed_settings,
    sanitize_legacy_opencode_config,
)


def test_install_claude_managed_settings_reads_utf8_bom_settings(tmp_path: Path) -> None:
    target_root = tmp_path / ".claude"
    target_root.mkdir()
    settings_path = target_root / "settings.json"
    settings_path.write_bytes(b"\xef\xbb\xbf" + b'{"existing": true}\n')

    materialized = install_claude_managed_settings(
        tmp_path,
        target_root,
        track_created_path=lambda _path: None,
        record_managed_json=lambda _path: None,
        record_merged_file=lambda _path, **_kwargs: None,
    )

    payload = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    assert materialized == [str(settings_path.resolve())]
    assert payload["existing"] is True
    assert payload["vibeskills"]["managed"] is True


def test_sanitize_legacy_opencode_config_reads_utf8_bom_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / "opencode.json"
    settings_path.write_bytes(b"\xef\xbb\xbf" + b'{"vibeskills": {"managed": true}}\n')

    receipt = sanitize_legacy_opencode_config(tmp_path)

    assert receipt["status"] == "removed-owned-node-and-deleted-empty-file"
    assert not settings_path.exists()
