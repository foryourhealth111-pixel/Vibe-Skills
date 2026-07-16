from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .policies import utc_now, write_text


def _load_receipt(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object in the Vibe install receipt: {path}")
    return payload


def evaluate_freshness(
    target_root: Path,
    *,
    write_artifacts: bool = False,
) -> tuple[bool, dict[str, Any]]:
    installed_root = (target_root / "skills" / "vibe").resolve()
    receipt_path = installed_root / ".vibeskills" / "install-receipt.json"
    failures: list[str] = []
    verified_file_count = 0

    receipt: dict[str, Any] = {}
    if not receipt_path.is_file():
        failures.append(f"Vibe install receipt is missing: {receipt_path}")
    else:
        try:
            receipt = _load_receipt(receipt_path)
        except (OSError, ValueError, RuntimeError) as exc:
            failures.append(str(exc))

    if receipt:
        if receipt.get("receipt_kind") != "vibe-skill-install":
            failures.append(f"unexpected Vibe install receipt kind: {receipt.get('receipt_kind')}")
        if receipt.get("skill_id") != "vibe":
            failures.append(f"unexpected installed skill id: {receipt.get('skill_id')}")
        if Path(str(receipt.get("install_root") or "")).resolve() != installed_root:
            failures.append(f"install receipt root does not match: {receipt.get('install_root')}")

        files = receipt.get("files")
        if not isinstance(files, list) or not files:
            failures.append("Vibe install receipt owns no runtime files")
        else:
            for entry in files:
                if not isinstance(entry, dict):
                    failures.append("invalid receipt file entry")
                    continue
                relative_path = str(entry.get("path") or "")
                expected_hash = str(entry.get("sha256") or "").lower()
                if not relative_path or len(expected_hash) != 64:
                    failures.append(f"invalid receipt entry: {relative_path}")
                    continue
                file_path = (installed_root / relative_path).resolve()
                try:
                    file_path.relative_to(installed_root)
                except ValueError:
                    failures.append(f"receipt path escapes installed runtime: {relative_path}")
                    continue
                if not file_path.is_file():
                    failures.append(f"missing receipt-owned file: {relative_path}")
                    continue
                actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    failures.append(f"hash mismatch: {relative_path}")
                    continue
                verified_file_count += 1

    gate_pass = not failures
    artifact = {
        "generated_at": utc_now(),
        "gate_result": "PASS" if gate_pass else "FAIL",
        "results": {
            "target_root": str(target_root.resolve()),
            "installed_root": str(installed_root),
            "receipt_path": str(receipt_path),
            "verified_file_count": verified_file_count,
            "failures": failures,
        },
    }

    for failure in failures:
        print(f"[FAIL] {failure}")
    if gate_pass:
        print(f"[PASS] installed runtime receipt verified ({verified_file_count} files)")

    if write_artifacts:
        write_text(
            installed_root / "outputs" / "verify" / "installed-runtime-freshness.json",
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        )

    return gate_pass, artifact


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the installed Vibe payload against its install receipt.")
    parser.add_argument("--target-root", default=str(Path.home() / ".agents"))
    parser.add_argument("--write-artifacts", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        gate_pass, _ = evaluate_freshness(
            Path(args.target_root),
            write_artifacts=args.write_artifacts,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0 if gate_pass else 1
