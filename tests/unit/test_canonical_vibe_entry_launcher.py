from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

import vgo_runtime.canonical_entry as canonical_entry


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_canonical_entry_writes_host_launch_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-ok"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    def fake_resolve_contract(repo_root: Path, host_id: str) -> dict[str, object]:
        assert repo_root == tmp_path.resolve()
        assert host_id == "codex"
        return {"fallback_policy": "blocked"}

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        assert kwargs["prompt"] == "plan runtime entry hardening"
        assert kwargs["requested_stage_stop"] == "phase_cleanup"
        _write_json(session_root / "runtime-input-packet.json", {"host_id": "codex", "requested_stage_stop": "phase_cleanup"})
        _write_json(session_root / "governance-capsule.json", {"runtime_selected_skill": "vibe"})
        _write_json(session_root / "stage-lineage.json", {"entries": [{"stage_name": "phase_cleanup"}]})
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "resolve_canonical_vibe_contract", fake_resolve_contract)
    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="plan runtime entry hardening",
        requested_stage_stop="phase_cleanup",
        artifact_root=tmp_path,
    )

    receipt_path = tmp_path / "outputs" / "runtime" / "vibe-sessions" / result.run_id / "host-launch-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["host_id"] == "codex"
    assert receipt["entry_id"] == "vibe"
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_rejects_non_blocked_fallback_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "allow"},
    )

    with pytest.raises(RuntimeError, match="unsupported fallback policy"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            artifact_root=tmp_path,
        )


def test_canonical_entry_requires_minimum_truth_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-missing"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked"},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_json(session_root / "runtime-input-packet.json", {"host_id": "codex"})
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="Missing required runtime artifacts"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            artifact_root=tmp_path,
        )


def test_canonical_entry_fails_when_runtime_packet_disagrees_with_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-mismatch"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked"},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_json(session_root / "runtime-input-packet.json", {"host_id": "claude-code", "requested_stage_stop": "phase_cleanup"})
        _write_json(session_root / "governance-capsule.json", {"runtime_selected_skill": "vibe"})
        _write_json(session_root / "stage-lineage.json", {"entries": [{"stage_name": "phase_cleanup"}]})
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="host_id mismatch"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_main_emits_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    result_payload = canonical_entry.CanonicalLaunchResult(
        run_id="run-1",
        session_root=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1",
        summary_path=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1" / "runtime-summary.json",
        host_launch_receipt_path=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1" / "host-launch-receipt.json",
        launch_mode="canonical-entry",
        summary={},
        artifacts={},
    )

    monkeypatch.setattr(canonical_entry, "launch_canonical_vibe", lambda **kwargs: result_payload)

    code = canonical_entry.main(
        [
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "hello",
        ]
    )

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "run-1"
    assert output["host_launch_receipt_path"].endswith("host-launch-receipt.json")
