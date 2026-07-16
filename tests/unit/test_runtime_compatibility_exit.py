from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.compatibility_exit import main, summarize_compatibility_exit


def test_summarize_compatibility_exit_covers_non_kernel_layers() -> None:
    payload = summarize_compatibility_exit(repo_root=REPO_ROOT)

    controlled = {entry["capability"]: entry for entry in payload["controlled_capabilities"]}
    assert set(controlled) == {"public_entry", "host_wiring"}
    assert controlled["public_entry"]["authority_layer"] == "entry_wrapper"
    assert controlled["host_wiring"]["authority_layer"] == "host_adapter"
    assert controlled["public_entry"]["primary_entry_file"] == "packages/runtime-core/src/vgo_runtime/canonical_entry.py"

    rules = {rule["id"] for rule in payload["non_negotiable_rules"]}
    assert "no-new-live-semantic-authority" in rules
    assert "zero-expansion-budget" in rules

    budgets = payload["phase_deletion_budgets"]
    assert [entry["phase"] for entry in budgets] == ["phase_1", "phase_2", "phase_3", "phase_4"]
    assert [entry["minimum_retirements"] for entry in budgets] == [0, 1, 2, 3]
    assert all(entry["maximum_new_compatibility_capabilities"] == 0 for entry in budgets)


def test_compatibility_exit_main_prints_json(capsys) -> None:
    assert main(["--repo-root", str(REPO_ROOT)]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["controlled_capabilities"][0]["capability"] == "public_entry"
    assert all(entry["capability"] != "compatibility_projection" for entry in payload["controlled_capabilities"])
