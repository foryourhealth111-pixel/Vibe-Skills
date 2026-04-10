from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
GOLDEN_FIXTURE = REPO_ROOT / "references" / "fixtures" / "runtime-contract" / "governed-runtime-root-golden.json"
TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def run_runtime(task: str, artifact_root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-contract-golden-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{RUNTIME_ENTRY}' "
                f"-Task '{TASK}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, **(extra_env or {}), "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(f"invoke-vibe-runtime returned empty payload. stderr={completed.stderr.strip()}")
    return json.loads(stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_hierarchy(hierarchy: dict[str, object]) -> dict[str, object]:
    return {
        "governance_scope": hierarchy["governance_scope"],
        "root_run_id": "<run_id>",
        "parent_run_id": hierarchy["parent_run_id"],
        "parent_unit_id": hierarchy["parent_unit_id"],
        "inherited_requirement_doc_path": hierarchy["inherited_requirement_doc_path"],
        "inherited_execution_plan_path": hierarchy["inherited_execution_plan_path"],
    }


def normalize_runtime_input_packet(packet: dict[str, object]) -> dict[str, object]:
    host_adapter = dict(packet["host_adapter"])
    return {
        "governance_scope": packet["governance_scope"],
        "runtime_mode": packet["runtime_mode"],
        "internal_grade": packet["internal_grade"],
        "hierarchy": normalize_hierarchy(dict(packet["hierarchy"])),
        "host_adapter": {
            "requested_id": host_adapter["requested_id"],
            "id": host_adapter["id"],
            "requested_host_id": host_adapter["requested_host_id"],
            "effective_host_id": host_adapter["effective_host_id"],
            "status": host_adapter["status"],
            "install_mode": host_adapter["install_mode"],
            "check_mode": host_adapter["check_mode"],
            "bootstrap_mode": host_adapter["bootstrap_mode"],
            "target_root": "<host_target_root>" if host_adapter["target_root"] else None,
            "closure_path": "<host_closure_path>" if host_adapter["closure_path"] else None,
        },
        "route_snapshot": {
            "selected_pack": packet["route_snapshot"]["selected_pack"],
            "selected_skill": packet["route_snapshot"]["selected_skill"],
            "route_mode": packet["route_snapshot"]["route_mode"],
            "route_reason": packet["route_snapshot"]["route_reason"],
            "confirm_required": packet["route_snapshot"]["confirm_required"],
            "confidence": packet["route_snapshot"]["confidence"],
            "truth_level": packet["route_snapshot"]["truth_level"],
            "degradation_state": packet["route_snapshot"]["degradation_state"],
            "non_authoritative": packet["route_snapshot"]["non_authoritative"],
            "fallback_active": packet["route_snapshot"]["fallback_active"],
            "hazard_alert_required": packet["route_snapshot"]["hazard_alert_required"],
            "unattended_override_applied": packet["route_snapshot"]["unattended_override_applied"],
            "custom_admission_status": packet["route_snapshot"]["custom_admission_status"],
        },
        "authority_flags": {
            "runtime_entry": packet["authority_flags"]["runtime_entry"],
            "explicit_runtime_skill": packet["authority_flags"]["explicit_runtime_skill"],
            "router_truth_level": packet["authority_flags"]["router_truth_level"],
            "shadow_only": packet["authority_flags"]["shadow_only"],
            "non_authoritative": packet["authority_flags"]["non_authoritative"],
            "allow_requirement_freeze": packet["authority_flags"]["allow_requirement_freeze"],
            "allow_plan_freeze": packet["authority_flags"]["allow_plan_freeze"],
            "allow_global_dispatch": packet["authority_flags"]["allow_global_dispatch"],
            "allow_completion_claim": packet["authority_flags"]["allow_completion_claim"],
        },
    }


def normalize_execution_manifest(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "governance_scope": manifest["governance_scope"],
        "mode": manifest["mode"],
        "internal_grade": manifest["internal_grade"],
        "hierarchy": normalize_hierarchy(dict(manifest["hierarchy"])),
        "authority": {
            "canonical_requirement_write_allowed": manifest["authority"]["canonical_requirement_write_allowed"],
            "canonical_plan_write_allowed": manifest["authority"]["canonical_plan_write_allowed"],
            "global_dispatch_allowed": manifest["authority"]["global_dispatch_allowed"],
            "completion_claim_allowed": manifest["authority"]["completion_claim_allowed"],
        },
        "route_runtime_alignment": {
            "router_selected_skill": manifest["route_runtime_alignment"]["router_selected_skill"],
            "runtime_selected_skill": manifest["route_runtime_alignment"]["runtime_selected_skill"],
            "skill_mismatch": manifest["route_runtime_alignment"]["skill_mismatch"],
            "confirm_required": manifest["route_runtime_alignment"]["confirm_required"],
            "requested_host_adapter_id": manifest["route_runtime_alignment"]["requested_host_adapter_id"],
            "effective_host_adapter_id": manifest["route_runtime_alignment"]["effective_host_adapter_id"],
        },
        "status": manifest["status"],
    }


class RuntimeContractGoldenTests(unittest.TestCase):
    def test_root_governed_runtime_matches_curated_packet_and_manifest_golden(self) -> None:
        fixture = load_json(GOLDEN_FIXTURE)

        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                TASK,
                artifact_root=Path(tempdir),
                extra_env={"VCO_HOST_ID": "codex"},
            )
            summary = payload["summary"]
            runtime_input_packet = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

        actual = {
            "runtime_input_packet": normalize_runtime_input_packet(runtime_input_packet),
            "execution_manifest": normalize_execution_manifest(execution_manifest),
        }

        self.assertEqual("runtime.contract.golden.v1", fixture["schema_version"])
        self.assertEqual(fixture["expected"], actual)
