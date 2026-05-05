from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "verify" / "vibe-current-routing-debt-gate.ps1"
POLICY = REPO_ROOT / "config" / "current-routing-debt-erasure.json"
OLD_ROLE_TERMS = [
    "route_authority_candidates",
    "stage_assistant_candidates",
    "route_authority_eligible",
    "legacy_role",
    "_legacy_role",
    "_legacy_stage_assistant_candidates",
]


def function_body(text: str, name: str) -> str:
    start = text.index(f"function {name}")
    next_start = text.find("\nfunction ", start + 1)
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def powershell() -> str:
    shell = (
        shutil.which("pwsh")
        or shutil.which("pwsh.exe")
        or shutil.which("powershell")
        or shutil.which("powershell.exe")
    )
    if not shell:
        pytest.skip("PowerShell executable not available")
    return shell


def run_gate(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [powershell(), "-NoLogo", "-NoProfile", "-File", str(GATE), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def copy_debt_gate_fixture(tmp_path: Path, *, current_paths: list[str]) -> Path:
    verify_dir = tmp_path / "scripts" / "verify"
    common_dir = tmp_path / "scripts" / "common"
    config_dir = tmp_path / "config"
    verify_dir.mkdir(parents=True, exist_ok=True)
    common_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".git").mkdir()

    shutil.copy2(GATE, verify_dir / GATE.name)
    shutil.copy2(REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1", common_dir / "vibe-governance-helpers.ps1")
    policy_payload = json.loads(POLICY.read_text(encoding="utf-8"))
    policy_payload["scan_scopes"]["current_paths"] = current_paths
    policy_payload["scan_scopes"]["legacy_allowed_paths"] = []
    (config_dir / POLICY.name).write_text(json.dumps(policy_payload, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(REPO_ROOT / "config" / "version-governance.json", config_dir / "version-governance.json")
    shutil.copy2(REPO_ROOT / "config" / "runtime-script-manifest.json", config_dir / "runtime-script-manifest.json")
    shutil.copy2(REPO_ROOT / "config" / "runtime-config-manifest.json", config_dir / "runtime-config-manifest.json")
    return verify_dir / GATE.name


def copy_debt_gate_policy_fixture(repo_root: Path, *, current_paths: list[str]) -> None:
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / ".git").mkdir(exist_ok=True)

    policy_payload = json.loads(POLICY.read_text(encoding="utf-8"))
    policy_payload["scan_scopes"]["current_paths"] = current_paths
    policy_payload["scan_scopes"]["legacy_allowed_paths"] = []
    (config_dir / POLICY.name).write_text(json.dumps(policy_payload, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(REPO_ROOT / "config" / "version-governance.json", config_dir / "version-governance.json")
    shutil.copy2(REPO_ROOT / "config" / "runtime-script-manifest.json", config_dir / "runtime-script-manifest.json")
    shutil.copy2(REPO_ROOT / "config" / "runtime-config-manifest.json", config_dir / "runtime-config-manifest.json")


def run_fixture_gate(gate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [powershell(), "-NoLogo", "-NoProfile", "-File", str(gate), "-Json"],
        cwd=gate.parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def run_fixture_gate_with_args(gate: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [powershell(), "-NoLogo", "-NoProfile", "-File", str(gate), *args],
        cwd=gate.parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def test_gate_reports_json_and_clean_current_surfaces() -> None:
    result = run_gate("-Json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["policy_path"].replace("\\", "/").endswith("config/current-routing-debt-erasure.json")
    assert payload["summary"]["P0"] == 0
    assert payload["summary"]["P1"] == 0
    assert payload["summary"]["P2"] == 0
    assert payload["summary"]["legacy_allowed_hits"] > 0
    assert "legacy_skill_routing" in payload["retired_terms"]
    assert "skill_routing.selected" in payload["current_fields"]
    assert payload["current_model"] == [
        "skill_candidates",
        "skill_routing.selected",
        "selected_skill_execution",
        "skill_usage.used",
        "skill_usage.unused",
        "skill_usage.evidence",
    ]


def test_gate_does_not_leave_python_bytecode_in_repo_owned_contracts() -> None:
    pycache = REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache)

    env = os.environ.copy()
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    result = run_gate("-Json", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not pycache.exists()


def test_gate_writes_audit_artifacts(tmp_path: Path) -> None:
    result = run_gate("-WriteArtifacts", "-ArtifactRoot", str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr

    json_path = tmp_path / "outputs" / "verify" / "current-routing-debt-gate.json"
    audit_json_path = tmp_path / "outputs" / "verify" / "current-routing-debt-audit.json"

    assert json_path.exists()
    assert audit_json_path.exists()

    gate_payload = json.loads(json_path.read_text(encoding="utf-8"))
    audit_payload = json.loads(audit_json_path.read_text(encoding="utf-8"))
    expected_audit_name = f"{gate_payload['generated_at'][:10]}-current-routing-debt-audit.md"
    audit_md_path = tmp_path / "docs" / "audits" / expected_audit_name
    repo_audit_md_path = REPO_ROOT / "docs" / "audits" / expected_audit_name

    assert audit_md_path.exists()
    assert not repo_audit_md_path.exists()
    audit_markdown = audit_md_path.read_text(encoding="utf-8")

    assert gate_payload["status"] == "pass"
    assert audit_payload["status"] == "pass"
    assert "# Current Routing Debt Audit" in audit_markdown
    assert "P0 Current Output Pollution: 0" in audit_markdown
    assert "P1 Current Code Dependency: 0" in audit_markdown
    assert "P2 Current Documentation Pollution: 0" in audit_markdown


def test_gate_policy_file_exists_and_is_valid_json() -> None:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["success_thresholds"] == {"P0": 0, "P1": 0, "P2": 0}


def test_gate_uses_thresholds_as_maximum_allowed_counts() -> None:
    text = GATE.read_text(encoding="utf-8")

    for priority in ("P0", "P1", "P2"):
        assert f"[int]$summary.{priority} -le [int]$policy.success_thresholds.{priority}" in text
        assert f"[int]$summary.{priority} -eq [int]$policy.success_thresholds.{priority}" not in text


def test_gate_scopes_retired_explanation_and_not_in_allowance_to_comments_or_strings() -> None:
    text = GATE.read_text(encoding="utf-8")

    assert "function Get-LineCommentAndStringFragments" in text
    retired_body = function_body(text, "Test-LineIsRetiredExplanation")
    guard_body = function_body(text, "Test-LineIsGuardAssertion")

    assert "Get-LineCommentAndStringFragments -Line $Line" in retired_body
    assert "$Line.IndexOf($needle" not in retired_body
    assert "Get-LineCommentAndStringFragments -Line $Line" in guard_body
    assert "foreach ($needle in @('assertNotIn', 'self.assertNotIn', 'assertNotRegex', 'assert \"not in\"', ' not in ', 'NotIn'))" not in guard_body
    assert "StartsWith('assert '" not in guard_body
    assert "$Line.IndexOf(' not in '" not in guard_body


def test_gate_does_not_treat_legacy_identifier_as_retired_explanation(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path, current_paths=["scripts/runtime"])
    runtime_dir = tmp_path / "scripts" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "example.ps1").write_text("$legacyObj = @{ stage_assistant_hints = $val }\n", encoding="utf-8")

    result = run_fixture_gate(gate)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["summary"]["P1"] == 1
    assert payload["findings"][0]["term"] == "stage_assistant_hints"


def test_gate_does_not_treat_non_assert_not_in_code_as_guard_assertion(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path, current_paths=["tests/runtime_neutral"])
    test_dir = tmp_path / "tests" / "runtime_neutral"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_example.py").write_text('if "legacy_skill_routing" not in payload:\n    pass\n', encoding="utf-8")

    result = run_fixture_gate(gate)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["summary"]["P1"] == 1
    assert payload["findings"][0]["term"] == "legacy_skill_routing"


def test_gate_treats_assert_not_in_retired_string_as_current_test_dependency(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path, current_paths=["tests/runtime_neutral"])
    test_dir = tmp_path / "tests" / "runtime_neutral"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_example.py").write_text('assert "stage_assistant_hints" not in payload\n', encoding="utf-8")

    result = run_fixture_gate(gate)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["summary"]["P1"] == 1
    assert payload["findings"][0]["term"] == "stage_assistant_hints"


def test_gate_does_not_treat_generic_notin_text_as_guard_assertion(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path, current_paths=["tests/runtime_neutral"])
    test_dir = tmp_path / "tests" / "runtime_neutral"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_example.py").write_text('VALUE = "stage_assistant_hints NotInitialized"\n', encoding="utf-8")

    result = run_fixture_gate(gate)
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["summary"]["P1"] == 1
    assert payload["findings"][0]["term"] == "stage_assistant_hints"


def test_repo_relative_path_requires_path_segment_boundary(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    sibling_file = tmp_path / "repo-tools" / "example.txt"
    sibling_file.parent.mkdir(parents=True, exist_ok=True)
    sibling_file.write_text("outside sibling\n", encoding="utf-8")

    function_source = function_body(GATE.read_text(encoding="utf-8"), "ConvertTo-RepoRelativePath")
    expected = str(sibling_file).replace("\\", "/")
    script = tmp_path / "check_repo_relative_boundary.ps1"
    script.write_text(
        "\n".join(
            [
                function_source,
                f"$result = ConvertTo-RepoRelativePath -Path {powershell_single_quoted(str(sibling_file))} -Root {powershell_single_quoted(str(root))}",
                f"$expected = {powershell_single_quoted(expected)}",
                'if ($result -ne $expected) { throw "Expected $expected but got $result" }',
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [powershell(), "-NoLogo", "-NoProfile", "-File", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_honors_explicit_repo_root_when_script_lives_elsewhere(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path / "script_repo", current_paths=["scripts/runtime"])
    scan_root = tmp_path / "scan_repo"
    copy_debt_gate_policy_fixture(scan_root, current_paths=["scripts/runtime"])
    runtime_dir = scan_root / "scripts" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "example.ps1").write_text("$payload = @{ stage_assistant_hints = 'legacy' }\n", encoding="utf-8")

    result = run_fixture_gate_with_args(gate, "-Json", "-RepoRoot", str(scan_root))
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert payload["repo_root"].replace("\\", "/") == scan_root.as_posix()
    assert payload["summary"]["P1"] == 1
    assert payload["findings"][0]["path"] == "scripts/runtime/example.ps1"
    assert payload["findings"][0]["term"] == "stage_assistant_hints"


def test_current_routing_debt_plan_uses_markdownlint_safe_structure() -> None:
    text = (REPO_ROOT / "docs" / "superpowers" / "plans" / "2026-05-02-current-routing-debt-erasure.md").read_text(
        encoding="utf-8"
    )

    assert "\n### Task " not in text
    assert "> old terms here are debt targets, not current runtime states.\n>\n> **For agentic workers:**" in text
    assert "````markdown\nCurrent routing debt:" in text
    assert "\n```markdown\nCurrent routing debt:" not in text


def test_gate_fails_when_configured_current_path_is_missing(tmp_path: Path) -> None:
    gate = copy_debt_gate_fixture(tmp_path, current_paths=["scripts/runtime/missing.ps1"])

    result = run_fixture_gate(gate)

    assert result.returncode != 0
    assert "Configured current_paths entry not found" in result.stdout + result.stderr


def test_immediate_technical_debt_register_uses_portable_scope() -> None:
    text = (REPO_ROOT / "docs" / "status" / "2026-05-03-immediate-technical-debt-register.md").read_text(
        encoding="utf-8"
    )

    assert "F:\\vibe" not in text
    assert "Scope: `Vibe-Skills`" in text


def test_gate_policy_scans_retired_old_role_fields() -> None:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    retired_terms = set(payload["retired_terms"])
    high_risk_terms = set(payload["high_risk_retired_fields"])

    for term in OLD_ROLE_TERMS:
        assert term in retired_terms
        assert term in high_risk_terms


def test_current_router_runtime_sources_do_not_contain_retired_old_role_fields() -> None:
    source_files = [
        REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_selection.py",
        REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_runtime.py",
        REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "custom_admission.py",
        REPO_ROOT / "scripts" / "router" / "modules" / "19-custom-admission.ps1",
        REPO_ROOT / "scripts" / "router" / "modules" / "41-candidate-selection.ps1",
        REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1",
        REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1",
    ]
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        for term in OLD_ROLE_TERMS:
            assert term not in text, f"{term} remains in {path}"


def test_runtime_packet_sibling_recommendations_use_neutral_ranking_language() -> None:
    text = (REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1").read_text(encoding="utf-8")

    assert "route_authority_eligible" not in text
    assert "additional XL route-authority specialist candidate" not in text
    assert "additional XL ranked specialist candidate" in text


def test_current_unit_and_integration_fixtures_do_not_write_retired_root_fields() -> None:
    current_fixture_files = [
        REPO_ROOT / "tests" / "unit" / "test_canonical_vibe_entry_launcher.py",
        REPO_ROOT / "tests" / "integration" / "test_verification_runtime_entrypoint_contract_cutover.py",
    ]
    for path in current_fixture_files:
        text = path.read_text(encoding="utf-8")
        assert '"specialist_recommendations"' not in text, path
        assert '"specialist_dispatch"' not in text, path
        assert '"legacy_skill_routing"' not in text, path


def test_truth_gate_legacy_fixture_is_named_as_retired_fixture() -> None:
    text = (REPO_ROOT / "tests" / "integration" / "test_canonical_vibe_truth_gate.py").read_text(encoding="utf-8")
    assert "def _write_retired_legacy_truth_artifacts(" in text
    assert "def _write_valid_canonical_entry_artifacts(" in text
    valid_helper = text.split("def _write_valid_canonical_entry_artifacts(", 1)[1].split(
        "def _write_retired_legacy_truth_artifacts(",
        1,
    )[0]
    assert '"legacy_skill_routing"' not in valid_helper
    assert '"specialist_recommendations"' not in valid_helper
    assert '"specialist_dispatch"' not in valid_helper
