from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_SOURCE_ROOTS = (
    "apps",
    "packages",
    "scripts",
    "config",
    "adapters",
    "core",
    "protocols",
)
ACTIVE_ROOT_FILES = (
    "SKILL.md",
    "install.ps1",
    "install.sh",
    "check.ps1",
    "check.sh",
)
CURRENT_GOVERNANCE_FILES = (
    "CONTRIBUTING.md",
    "docs/developer-change-governance.md",
    "docs/contributor-default-runbooks.md",
    "docs/operator-default-runbooks.md",
    "references/runtime-contract-schema-reference.md",
    "references/runtime-contract-schema.md",
)
CURRENT_STATUS_FILES = (
    "docs/status/kernel-first-remediation-phase-summary.md",
    "docs/status/test-governance-classification-matrix.md",
)
CURRENT_SCENARIO_FILES = (
    "tests/scenarios/project_delivery/l-grade-feature-complete.json",
    "tests/scenarios/project_delivery/xl-composite-manual-review.json",
)
EXECUTION_CONTRACT_FILES = (
    "protocols/team.md",
    "references/runtime-contract-schema.md",
    "references/runtime-contract-schema-reference.md",
    "references/runtime-contract-field-contract.md",
    "docs/governance/vibe-governed-project-delivery-acceptance-governance.md",
    "docs/governance/role-pack-v2-governance.md",
    "docs/role-pack-v2-governance.md",
)
TEXT_SUFFIXES = {".json", ".md", ".ps1", ".py", ".sh", ".yaml", ".yml"}
AGENT_HANDOFF_ARTIFACTS = (
    "module-work-plan.json",
    "agent-execution-handoff.json",
    "module-execution.json",
)
CURRENT_SURFACE_RETIRED_TERMS = (
    "specialist",
    "binary_skill_usage",
    "native_execution_topology",
    "direct_current_session",
)
TEST_PATH_PATTERN = re.compile(r"tests/[A-Za-z0-9_./-]+\.py")

RETIRED_EXECUTION_TERMS = (
    "direct_current_session_routed",
    "direct_current_session_route",
    "native_specialist_execution",
    "native-specialist-execution",
    "native specialist execution",
    "native_specialist_runner",
    "direct_specialist_execution",
    "direct-specialist-execution",
    "direct specialist execution",
    "native_skill_entrypoint",
    "skill_execution_contract",
    "host_skill_execution_contract",
    "skill_execution_unit_count",
    "executed_skill_execution_units",
    "failed_skill_execution_units",
    "blocked_skill_execution_units",
    "degraded_skill_execution_units",
    "execution_skill_outcomes",
    "specialist_accounting",
    "specialist_decision",
    "specialist_user_disclosure",
    "module_skill_dispatch_fallback",
    "runtime_packet_selected_skill_source",
    "selected_skill_ids_source",
    "skill_usage",
    "skill_usage_truth",
    "used_skill_ids",
    "unused_skill_ids",
    "execution_topology",
    "execution_topology_path",
    "execution_proof_manifest",
    "executed_unit_count",
    "timed_out_unit_count",
    "skill_read_receipt",
    "skill_load_receipt",
    "skill_execution_hash",
    "skill_execution_digest",
    "New-VibeBlockedSpecialistDispatchResult",
)

# These references remove or assert the absence of retired fields. They do not
# restore a writer, reader, fallback, or independent usage ledger.
RETIREMENT_GUARDS = {
    "config/current-routing-debt-erasure.json": {
        "skill_usage",
        "used_skill_ids",
        "unused_skill_ids",
        "execution_topology",
        "execution_topology_path",
        "execution_proof_manifest",
    },
    "config/routing-terminology-hard-cleanup.json": {
        "execution_topology",
        "execution_proof_manifest",
    },
    "references/runtime-contract-schema-reference.md": {
        "specialist_accounting",
        "specialist_decision",
    },
    "references/runtime-contract-schema.md": {
        "specialist_accounting",
        "specialist_decision",
    },
    "scripts/verify/vibe-canonical-entry-truth-gate.ps1": {"skill_usage"},
    "scripts/verify/vibe-no-silent-fallback-contract-gate.ps1": {"skill_usage"},
}

MCP_ACTION_TERMS = (
    "install",
    "provision",
    "register",
    "recommend",
    "enable",
    "offer",
    "安装",
    "注册",
    "推荐",
    "启用",
)
MCP_NEGATION_TERMS = (
    "forbid",
    "excluded",
    "do not",
    "must not",
    "never",
    "remove",
    "retired",
    "disabled",
    "禁止",
    "不得",
    "移除",
    "禁用",
)
EXPECTED_FORBIDDEN_MCP_IDS = {
    "chrome",
    "chrome-devtools",
    "playwright",
    "context7",
    "claude-flow",
}


def _active_paths() -> list[Path]:
    paths = [REPO_ROOT / relative_path for relative_path in (*ACTIVE_ROOT_FILES, *CURRENT_GOVERNANCE_FILES)]
    for root_name in ACTIVE_SOURCE_ROOTS:
        root = REPO_ROOT / root_name
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
    for path in (REPO_ROOT / "docs/governance").glob("*.md"):
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
        if not re.search(r"\d{4}-\d{2}-\d{2}|historical|retired note|superseded", path.name + head, re.I):
            paths.append(path)
    return sorted(set(paths))


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _retired_terms(text: str) -> set[str]:
    lowered = text.casefold()
    return {
        term
        for term in RETIRED_EXECUTION_TERMS
        if re.search(rf"(?<![a-z0-9_]){re.escape(term.casefold())}(?![a-z0-9_])", lowered)
    }


def _forbidden_mcp_guidance_hits(text: str, forbidden_ids: set[str]) -> list[tuple[int, str]]:
    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        window = "\n".join(lines[max(0, index - 3) : index + 4]).casefold()
        if "mcp" not in window or not any(term in window for term in MCP_ACTION_TERMS):
            continue
        if any(term in window for term in MCP_NEGATION_TERMS):
            continue
        for mcp_id in forbidden_ids:
            if re.search(rf"(?<![a-z0-9_-]){re.escape(mcp_id)}(?![a-z0-9_-])", line.casefold()):
                hits.append((index + 1, mcp_id))
    return hits


def _referenced_test_paths(text: str) -> set[str]:
    return set(TEST_PATH_PATTERN.findall(text))


def test_active_runtime_has_no_new_retired_execution_or_accounting_surface() -> None:
    unexpected: dict[str, list[str]] = {}
    for path in _active_paths():
        terms = _retired_terms(path.read_text(encoding="utf-8"))
        terms -= RETIREMENT_GUARDS.get(_relative(path), set())
        if terms:
            unexpected[_relative(path)] = sorted(terms)

    assert not unexpected, f"Retired Agent-execution surfaces remain active: {unexpected}"


def test_current_execution_contracts_use_agent_handoff_artifacts() -> None:
    retired_terms = (
        "execution_topology",
        "execution-topology",
        "execution topology",
        "execution_proof_manifest",
        "direct current-session specialist",
        "native specialist",
    )
    contract_hits: dict[str, list[str]] = {}
    required_artifacts = (
        "module-work-plan.json",
        "agent-execution-handoff.json",
        "module-execution.json",
    )
    for relative_path in EXECUTION_CONTRACT_FILES:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8").casefold()
        hits = [term for term in retired_terms if term in text]
        if hits:
            contract_hits[relative_path] = hits
        assert all(artifact in text for artifact in required_artifacts), relative_path

    assert not contract_hits, f"Retired execution-topology narratives remain: {contract_hits}"

    proof_registry = json.loads(
        (REPO_ROOT / "config/proof-class-registry.json").read_text(encoding="utf-8")
    )
    artifact_defaults = proof_registry["artifact_class_defaults"]
    assert "execution_proof_manifest" not in artifact_defaults
    assert artifact_defaults["module_execution"] == "runtime"

    debt_policy = json.loads(
        (REPO_ROOT / "config/current-routing-debt-erasure.json").read_text(encoding="utf-8")
    )
    current_model = debt_policy["current_model"]
    chain_start = current_model.index("module-work-plan.json")
    assert current_model[chain_start : chain_start + 3] == list(required_artifacts)
    assert {
        "execution_topology",
        "execution_topology_path",
        "execution_proof_manifest",
    }.issubset(debt_policy["high_risk_retired_fields"])

    cleanup_policy = json.loads(
        (REPO_ROOT / "config/routing-terminology-hard-cleanup.json").read_text(encoding="utf-8")
    )
    assert "tests/runtime_neutral/test_retired_agent_execution_surfaces.py" in cleanup_policy[
        "current_behavior_tests"
    ]
    assert "tests/runtime_neutral/test_l_xl_agent_execution_handoff.py" not in cleanup_policy[
        "current_behavior_tests"
    ]
    assert set(retired_terms).issubset(cleanup_policy["current_policy_helper_forbidden_patterns"])

    topology_policy_ref = "config/execution-topology-policy.json"
    production_reads_policy = topology_policy_ref in (
        REPO_ROOT / "scripts/runtime/VibeRuntime.Common.ps1"
    ).read_text(encoding="utf-8").replace("\\", "/")
    config_manifest = json.loads(
        (REPO_ROOT / "config/runtime-config-manifest.json").read_text(encoding="utf-8")
    )
    if production_reads_policy:
        assert (REPO_ROOT / topology_policy_ref).is_file()
        assert topology_policy_ref in config_manifest["files"]
    else:
        assert not (REPO_ROOT / topology_policy_ref).exists()
        assert topology_policy_ref not in config_manifest["files"]


def test_public_and_current_architecture_docs_do_not_publish_retired_execution_owners() -> None:
    public_docs = {
        "README.md": ("specialist decision truth", "leaf execution"),
        "README.zh.md": ("专家决策真相", "叶子执行"),
        "docs/governance/current-runtime-field-contract.md": ("specialist_decision",),
        "docs/architecture/legacy-topology-audit.md": (
            "Invoke-DelegatedLaneUnit",
            "VibeExecution.Common",
        ),
    }
    problems: dict[str, list[str]] = {}
    for relative_path, retired_phrases in public_docs.items():
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        hits = [phrase for phrase in retired_phrases if phrase.casefold() in text.casefold()]
        if hits:
            problems[relative_path] = hits

    current_chain = (
        "agent_skill_organization -> module-work-plan.json -> "
        "agent-execution-handoff.json -> module-execution.json"
    )
    for relative_path in (
        "docs/governance/absorption-admission-matrix.md",
        "docs/governance/connector-scorecard-governance.md",
    ):
        head = "\n".join(
            (REPO_ROOT / relative_path).read_text(encoding="utf-8").splitlines()[:5]
        )
        if "skill_usage" in head or current_chain not in head:
            problems[relative_path] = ["historical note publishes the wrong current truth chain"]

    assert not problems, problems


def test_current_status_and_scenarios_publish_live_agent_handoff_truth() -> None:
    problems: dict[str, object] = {}
    contract = json.loads(
        (REPO_ROOT / "config/project-delivery-acceptance-contract.json").read_text(encoding="utf-8")
    )
    expected_truth_layers = set(contract["truth_layers"])

    for relative_path in (*CURRENT_STATUS_FILES, *CURRENT_SCENARIO_FILES):
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        lowered = text.casefold()
        retired_terms = _retired_terms(text)
        retired_terms.update(term for term in CURRENT_SURFACE_RETIRED_TERMS if term in lowered)
        if retired_terms:
            problems[f"{relative_path}:retired_terms"] = sorted(retired_terms)

        missing_test_paths = sorted(
            path for path in _referenced_test_paths(text) if not (REPO_ROOT / path).is_file()
        )
        if missing_test_paths:
            problems[f"{relative_path}:missing_test_paths"] = missing_test_paths

    for relative_path in CURRENT_SCENARIO_FILES:
        scenario = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        actual_truth_layers = set(scenario["truths"])
        if actual_truth_layers != expected_truth_layers:
            problems[f"{relative_path}:truth_layers"] = {
                "missing": sorted(expected_truth_layers - actual_truth_layers),
                "unexpected": sorted(actual_truth_layers - expected_truth_layers),
            }

        scenario_text = json.dumps(scenario, ensure_ascii=False).casefold()
        missing_artifacts = [
            artifact for artifact in AGENT_HANDOFF_ARTIFACTS if artifact not in scenario_text
        ]
        if missing_artifacts:
            problems[f"{relative_path}:missing_handoff_artifacts"] = missing_artifacts

    assert not problems, f"Current public surfaces publish stale Agent execution truth: {problems}"


def test_current_plans_and_upstream_lock_name_the_agent_as_execution_owner() -> None:
    earlier_plan = REPO_ROOT / "docs/plans/2026-07-12-vibe-module-driven-orchestration-kernel-execution-plan.md"
    plan_head = "\n".join(earlier_plan.read_text(encoding="utf-8").splitlines()[:20]).casefold()
    assert "superseded" in plan_head
    assert "2026-07-12-vibe-agent-execution-handoff-control-flow-repair-plan.md" in plan_head
    assert "current agent" in plan_head
    assert "module-execution.json" in plan_head

    upstream_lock = json.loads((REPO_ROOT / "config/upstream-lock.json").read_text(encoding="utf-8"))
    serialized = json.dumps(upstream_lock, ensure_ascii=False).casefold()
    assert "specialist execution comes from locally installed skills" not in serialized
    for dependency_id in ("obra/superpowers", "github/spec-kit"):
        dependency = next(item for item in upstream_lock["dependencies"] if item["id"] == dependency_id)
        next_action = str(dependency["next_action"]).casefold()
        assert "current agent" in next_action
        assert "approved module plan" in next_action


def test_forbidden_mcp_policy_is_exact_and_scannable() -> None:
    policy = json.loads((REPO_ROOT / "config/forbidden-mcp-policy.json").read_text(encoding="utf-8"))

    assert policy["applies_to"] == "mcp_server_ids"
    assert policy["id_match"] == "exact"
    assert set(policy["non_mcp_exclusions"]) == {
        "ordinary_installation_receipts",
        "file_integrity_hashes",
        "host_native_capabilities",
    }

    forbidden_ids = {str(value).casefold() for value in policy["forbidden_mcp_ids"]}
    assert forbidden_ids == EXPECTED_FORBIDDEN_MCP_IDS
    hits = {
        _relative(path): _forbidden_mcp_guidance_hits(path.read_text(encoding="utf-8"), forbidden_ids)
        for path in _active_paths()
        if _relative(path) != "config/forbidden-mcp-policy.json"
    }
    hits = {path: matches for path, matches in hits.items() if matches}
    assert not hits, f"Forbidden MCP installation or recommendation remains active: {hits}"


def test_static_scan_does_not_confuse_unrelated_receipts_hashes_or_native_capabilities() -> None:
    unrelated = (
        "Verify the ordinary installation receipt.\n"
        "SKILL.md hashes match the file-integrity lock.\n"
        "Use host-native tools already allowed by host policy.\n"
        "Use the Playwright skill for browser automation."
    )

    assert not _retired_terms(unrelated)
    assert not _forbidden_mcp_guidance_hits(unrelated, {"playwright"})
    assert _retired_terms("direct_current_session_routed") == {"direct_current_session_routed"}
    assert _forbidden_mcp_guidance_hits("Recommend the Playwright MCP server.", {"playwright"}) == [
        (1, "playwright")
    ]
