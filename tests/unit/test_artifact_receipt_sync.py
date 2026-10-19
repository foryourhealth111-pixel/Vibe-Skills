from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages/runtime-core/src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

import vgo_runtime.artifact_contract as artifacts


def _projection(tmp_path: Path) -> artifacts.RuntimeArtifactProjection:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    projection = artifacts.resolve_runtime_artifact_projection(
        agent_root=workspace, workspace_root=workspace, run_id="receipt-sync", repo_root=REPO_ROOT,
    )
    projection.session_root.mkdir(parents=True)
    projection.run_root.mkdir(parents=True)
    return projection


def test_receipt_sync_replaces_hardlink_without_modifying_external_file(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    external = tmp_path / "external-user-file.json"
    external.write_text("user original\n", encoding="utf-8")
    destination = projection.run_root / "module-execution.json"
    try:
        os.link(external, destination)
    except OSError as exc:
        pytest.skip(f"Hard links unavailable: {exc}")
    (projection.session_root / destination.name).write_text("runtime replacement\n", encoding="utf-8")
    artifacts.sync_session_receipts_to_run_artifact_sink(projection, session_root=projection.session_root)
    assert external.read_text(encoding="utf-8") == "user original\n"
    assert destination.read_text(encoding="utf-8") == "runtime replacement\n"


@pytest.mark.parametrize("existing", [False, True])
def test_receipt_sync_copy_failure_preserves_destination_and_removes_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool) -> None:
    projection = _projection(tmp_path)
    destination = projection.run_root / "module-execution.json"
    if existing:
        destination.write_text("accepted result\n", encoding="utf-8")
    (projection.session_root / destination.name).write_text("new result\n", encoding="utf-8")
    before = {path.relative_to(projection.run_root): path.read_bytes() for path in projection.run_root.rglob("*") if path.is_file()}

    def interrupted_copy(source: Path, target: Path) -> None:
        Path(target).write_text("partial bytes", encoding="utf-8")
        raise OSError("copy interrupted")

    monkeypatch.setattr(artifacts, "copy2", interrupted_copy)
    with pytest.raises(OSError, match="copy interrupted"):
        artifacts.sync_session_receipts_to_run_artifact_sink(projection, session_root=projection.session_root)
    assert before == {path.relative_to(projection.run_root): path.read_bytes() for path in projection.run_root.rglob("*") if path.is_file()}


def test_receipt_sync_copies_regular_file(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    (projection.session_root / "module-execution.json").write_text("runtime output\n", encoding="utf-8")
    artifacts.sync_session_receipts_to_run_artifact_sink(projection, session_root=projection.session_root)
    assert (projection.run_root / "module-execution.json").read_text(encoding="utf-8") == "runtime output\n"
