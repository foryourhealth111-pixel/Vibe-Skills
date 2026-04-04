from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "universalization" / "host-capability-matrix.md"
ADAPTER_ROOT = REPO_ROOT / "adapters"


def _read_host_matrix_rows() -> list[dict[str, str]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    try:
        matrix_start = lines.index("## Host Matrix")
    except ValueError as exc:
        raise AssertionError("missing host matrix section") from exc

    rows: list[dict[str, str]] = []
    for line in lines[matrix_start + 3 :]:
        if not line.startswith("|"):
            break
        if set(line.replace("|", "").replace("-", "").replace(" ", "")) == set():
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 7:
            raise AssertionError(f"unexpected host matrix column count: {line}")
        rows.append(
            {
                "host": parts[0],
                "status": parts[1].strip("`") if parts[1].startswith("`") else parts[1],
                "runtime_role": parts[2].strip("`") if parts[2].startswith("`") else parts[2],
                "settings_contract": parts[3],
                "plugin_mcp_contract": parts[4],
                "release_closure": parts[5],
                "notes": parts[6],
            }
        )
    return rows


def _read_host_profiles() -> dict[str, dict[str, str]]:
    profiles: dict[str, dict[str, str]] = {}
    for path in sorted(ADAPTER_ROOT.glob("*/host-profile.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        profiles[data["host_name"]] = {
            "status": data["status"],
            "runtime_role": data["runtime_role"],
        }
    return profiles


def test_host_capability_matrix_has_unique_host_rows() -> None:
    hosts = [row["host"] for row in _read_host_matrix_rows()]
    duplicates = {host: count for host, count in Counter(hosts).items() if count > 1}

    assert not duplicates, f"duplicate host rows in host capability matrix: {duplicates}"


def test_host_capability_matrix_matches_host_profiles_on_disk() -> None:
    rows = _read_host_matrix_rows()
    row_by_host = {row["host"]: row for row in rows}
    profiles = _read_host_profiles()

    assert set(row_by_host) == set(profiles), (
        "host capability matrix must cover each discovered host profile exactly once: "
        f"rows={sorted(row_by_host)} profiles={sorted(profiles)}"
    )

    for host_name, profile in profiles.items():
        row = row_by_host[host_name]
        assert row["status"] == profile["status"], f"status mismatch for {host_name}"
        assert row["runtime_role"] == profile["runtime_role"], f"runtime_role mismatch for {host_name}"
