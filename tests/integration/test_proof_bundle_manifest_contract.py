from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROOF_BUNDLES_ROOT = REPO_ROOT / "references" / "proof-bundles"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_manifest_paths() -> list[Path]:
    manifests = sorted(PROOF_BUNDLES_ROOT.glob("*/manifest.json"))
    manifests.extend(sorted(PROOF_BUNDLES_ROOT.glob("*/baseline-manifest.json")))
    return manifests


def _assert_repo_paths_exist(paths: list[str], *, owner: Path, field_name: str) -> None:
    missing = [rel for rel in paths if not (REPO_ROOT / rel).exists()]
    assert not missing, f"{owner.relative_to(REPO_ROOT)} has missing {field_name}: {missing}"


def _assert_receipt_file_matches_tree(bundle_dir: Path) -> None:
    receipt_file = bundle_dir / "receipt-files.txt"
    if not receipt_file.exists():
        return

    missing = []
    for raw_line in receipt_file.read_text(encoding="utf-8").splitlines():
        raw_path = raw_line.strip().replace("\\", "/")
        if not raw_path:
            continue
        candidate: Path
        if raw_path.startswith("/bundle/"):
            candidate = bundle_dir / raw_path.removeprefix("/bundle/")
        elif raw_path.startswith("/"):
            marker = "/references/proof-bundles/"
            if marker in raw_path:
                repo_relative = raw_path.split(marker, 1)[1]
                candidate = REPO_ROOT / "references" / "proof-bundles" / repo_relative
            else:
                candidate = Path(raw_path)
        else:
            candidate = bundle_dir / raw_path

        if not candidate.exists():
            missing.append(raw_path)

    assert not missing, (
        f"{receipt_file.relative_to(REPO_ROOT)} lists missing bundle artifacts: {missing}"
    )


def test_proof_bundle_manifests_only_reference_existing_repo_paths() -> None:
    manifest_paths = _iter_manifest_paths()
    assert manifest_paths, "expected at least one proof-bundle manifest"

    for manifest_path in manifest_paths:
        data = _load_json(manifest_path)
        repo_path_fields = [
            "gate_script",
            "contracts",
            "required_gates",
            "required_fresh_machine_reports",
            "required_replay_sync",
            "authority_contracts",
            "minimum_non_regression_gates",
        ]

        for field_name in repo_path_fields:
            raw_value = data.get(field_name)
            if raw_value is None:
                continue
            if isinstance(raw_value, str):
                paths = [raw_value]
            elif isinstance(raw_value, dict):
                paths = [str(item) for item in raw_value.values() if isinstance(item, str)]
            else:
                paths = [str(item) for item in raw_value]
            _assert_repo_paths_exist(paths, owner=manifest_path, field_name=field_name)


def test_proof_bundle_run_artifacts_exist_for_declared_required_files() -> None:
    for manifest_path in _iter_manifest_paths():
        data = _load_json(manifest_path)
        run_groups: list[dict[str, object]] = []
        for field_name, value in data.items():
            if (field_name.endswith("_runs") or field_name == "frozen_runs") and isinstance(value, list):
                run_groups.extend(value)

        for run in run_groups:
            bundle_dir = REPO_ROOT / str(run["bundle_dir"])
            operation_record = REPO_ROOT / str(run["operation_record"])

            assert bundle_dir.is_dir(), (
                f"missing bundle_dir for {manifest_path.relative_to(REPO_ROOT)}: {run['bundle_dir']}"
            )
            assert operation_record.exists(), (
                f"missing operation_record for {manifest_path.relative_to(REPO_ROOT)}: {run['operation_record']}"
            )

            required_files = [bundle_dir / str(rel) for rel in run.get("required_files", [])]
            missing = [str(path.relative_to(REPO_ROOT)) for path in required_files if not path.exists()]
            assert not missing, (
                f"{manifest_path.relative_to(REPO_ROOT)} declares missing run artifacts: {missing}"
            )

            _assert_receipt_file_matches_tree(bundle_dir)
