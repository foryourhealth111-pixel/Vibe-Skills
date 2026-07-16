from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _public_entry_ids() -> set[str]:
    payload = json.loads(_read("config/vibe-entry-surfaces.json"))
    return {
        entry["id"]
        for entry in payload["entries"]
        if entry.get("publicly_exposed") is True
    }


def test_readmes_describe_only_public_vibe_entry_surface() -> None:
    assert _public_entry_ids() == {"vibe"}

    for path in ("README.md", "README.zh.md", "docs/quick-start.en.md", "docs/quick-start.md"):
        content = _read(path)
        assert "vibe-upgrade" not in content
        assert "vibe-what-do-i-want" not in content
        assert "vibe-how-do-we-do" not in content
        assert "vibe-do-it" not in content
        assert "host-rendered" not in content
        assert "宿主渲染标签" not in content
        for legacy_alias in ("vibe-want", "vibe-how", "vibe-do"):
            assert re.search(rf"(?<![\w-]){re.escape(legacy_alias)}(?![\w-])", content) is None


def test_root_skill_keeps_update_on_the_command_path_not_a_public_skill() -> None:
    content = _read("SKILL.md")

    assert "vibe-upgrade" not in content
    assert "update" in content
    assert "--skills-dir" in content


def test_governance_navigation_separates_current_contracts_from_archived_history() -> None:
    governance_readme = _read("docs/governance/README.md")
    archive_readme = _read("docs/archive/governance-history/README.md")

    for current_doc in (
        "current-runtime-field-contract.md",
        "current-routing-contract.md",
        "skill-admission-hardening.md",
        "bundled-skill-retention-matrix.md",
        "kernel-first-remediation-baseline.md",
    ):
        assert current_doc in governance_readme

    for archived_doc in (
        "zero-route-authority-pack-consolidation-2026-04-29.md",
        "zero-route-authority-second-pass-2026-04-29.md",
        "zero-route-authority-third-pass-2026-04-30.md",
    ):
        assert archived_doc not in governance_readme
        assert archived_doc in archive_readme
        assert not (REPO_ROOT / "docs" / "governance" / archived_doc).exists()
        assert (REPO_ROOT / "docs" / "archive" / "governance-history" / archived_doc).exists()


def test_status_navigation_keeps_historical_dry_run_out_of_start_here() -> None:
    status_readme = _read("docs/status/README.md")

    start_here = status_readme[status_readme.index("## Start Here"):].split("## Cross-Layer Handoff", 1)[0]
    reading_boundary = status_readme[status_readme.index("## Reading Boundary"):].split("## Rules", 1)[0]
    historical_dry_run = "[`operator-dry-run.md`](operator-dry-run.md)"

    assert historical_dry_run not in start_here
    assert historical_dry_run in reading_boundary


def test_status_navigation_keeps_history_index_out_of_start_here() -> None:
    status_readme = _read("docs/status/README.md")

    start_here = status_readme[status_readme.index("## Start Here"):].split("## Cross-Layer Handoff", 1)[0]
    reading_boundary = status_readme[status_readme.index("## Reading Boundary"):].split("## Rules", 1)[0]
    history_index = "[`history-index.md`](./history-index.md)"

    assert history_index not in start_here
    assert history_index in reading_boundary


def test_status_navigation_keeps_operator_script_index_out_of_cross_layer_handoff() -> None:
    status_readme = _read("docs/status/README.md")

    cross_layer = status_readme[status_readme.index("## Cross-Layer Handoff"):].split("## Reading Boundary", 1)[0]
    rules_section = status_readme[status_readme.index("## Rules"):].splitlines()
    operator_scripts = "[`../../scripts/README.md`](../../scripts/README.md)"

    assert operator_scripts not in cross_layer
    assert any(operator_scripts in line for line in rules_section)


def test_status_navigation_keeps_verify_run_order_index_out_of_cross_layer_handoff() -> None:
    status_readme = _read("docs/status/README.md")

    cross_layer = status_readme[status_readme.index("## Cross-Layer Handoff"):].split("## Reading Boundary", 1)[0]
    rules_section = status_readme[status_readme.index("## Rules"):].splitlines()
    verify_run_order = "[`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md)"

    assert verify_run_order not in cross_layer
    assert any(verify_run_order in line for line in rules_section)


def test_docs_root_keeps_plans_index_out_of_start_here() -> None:
    docs_readme = _read("docs/README.md")

    start_here = docs_readme[docs_readme.index("## Start Here"):].split("## 按需再看", 1)[0]
    cross_layer = docs_readme[docs_readme.index("## Cross-Layer Handoff"):].split("## Rules", 1)[0]
    plans_link = "[`plans/README.md`](./plans/README.md)"

    assert plans_link not in start_here
    assert plans_link in cross_layer


def test_docs_root_keeps_scripts_index_out_of_cross_layer_handoff() -> None:
    docs_readme = _read("docs/README.md")

    cross_layer = docs_readme[docs_readme.index("## Cross-Layer Handoff"):].split("## Rules", 1)[0]
    rules_section = docs_readme[docs_readme.index("## Rules"):].splitlines()
    scripts_link = "[`../scripts/README.md`](../scripts/README.md)"

    assert scripts_link not in cross_layer
    assert any(scripts_link in line for line in rules_section)


def test_design_readme_keeps_verify_entry_index_out_of_cross_layer_handoff() -> None:
    design_readme = _read("docs/design/README.md")

    cross_layer = design_readme[design_readme.index("## Cross-Layer Handoff"):].split("## Rules", 1)[0]
    rules_section = design_readme[design_readme.index("## Rules"):].splitlines()
    verify_link = "[`../../scripts/verify/README.md`](../../scripts/verify/README.md)"

    assert verify_link not in cross_layer
    assert any(verify_link in line for line in rules_section)


def test_external_tooling_readme_keeps_operator_script_index_out_of_cross_layer_handoff() -> None:
    tooling_readme = _read("docs/external-tooling/README.md")

    cross_layer = tooling_readme[tooling_readme.index("### Cross-Layer Handoff"):].split("## Rules", 1)[0]
    rules_section = tooling_readme[tooling_readme.index("## Rules"):].splitlines()
    scripts_link = "[`../../scripts/README.md`](../../scripts/README.md)"

    assert scripts_link not in cross_layer
    assert any(scripts_link in line for line in rules_section)


def test_public_readmes_do_not_link_directly_to_test_files() -> None:
    english = _read("README.md")
    chinese = _read("README.zh.md")

    assert "./tests/" not in english
    assert "./tests/" not in chinese
    assert "test_codex_memory_user_simulation.py" not in english
    assert "test_codex_memory_user_simulation.py" not in chinese
    assert "docs/status/non-regression-proof-bundle.md" in english
    assert "docs/status/non-regression-proof-bundle.md" in chinese


def test_release_navigation_keeps_archive_links_out_of_runtime_proof_handoff() -> None:
    release_readme = _read("docs/releases/README.md")

    proof_handoff = release_readme[release_readme.index("### Release Runtime / Proof Handoff"):].split(
        "## Recent Governed Releases",
        1,
    )[0]
    historical_archive = release_readme[release_readme.index("## Historical Release Archive"):].split(
        "## Historical Packetization",
        1,
    )[0]
    historical_packetization = release_readme[release_readme.index("## Historical Packetization"):].split(
        "## Release Operator Entry",
        1,
    )[0]

    archive_link = "[`../archive/releases/README.md`](../archive/releases/README.md)"
    packet_link = "[`../archive/releases/wave15-18-release-packet.md`](../archive/releases/wave15-18-release-packet.md)"

    assert archive_link not in proof_handoff
    assert archive_link in historical_archive
    assert packet_link not in proof_handoff
    assert packet_link in historical_packetization


def test_release_navigation_keeps_exact_gate_script_names_out_of_runtime_proof_handoff() -> None:
    release_readme = _read("docs/releases/README.md")

    proof_handoff = release_readme[release_readme.index("### Release Runtime / Proof Handoff"):].split(
        "## Recent Governed Releases",
        1,
    )[0]

    assert "vibe-skill-promotion-execution-gate.ps1" not in proof_handoff
    assert "vibe-release-truth-consistency-gate.ps1" not in proof_handoff
    assert "[`../../scripts/verify/README.md`](../../scripts/verify/README.md)" in proof_handoff
    assert "[`../status/non-regression-proof-bundle.md`](../status/non-regression-proof-bundle.md)" in proof_handoff


def test_release_navigation_keeps_gate_family_index_out_of_runtime_proof_handoff() -> None:
    release_readme = _read("docs/releases/README.md")

    proof_handoff = release_readme[release_readme.index("### Release Runtime / Proof Handoff"):].split(
        "## Recent Governed Releases",
        1,
    )[0]
    rules_section = release_readme[release_readme.index("## Rules"):].splitlines()

    gate_index_link = "[`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md)"

    assert gate_index_link not in proof_handoff
    assert any(gate_index_link in line for line in rules_section)
    assert "[`../../scripts/verify/README.md`](../../scripts/verify/README.md)" in proof_handoff


def test_readmes_describe_local_installed_skill_story_without_repromoting_a_central_catalog() -> None:
    english = _read("README.md")
    chinese = _read("README.zh.md")
    english_lower = english.lower()
    chinese_lower = chinese.lower()

    assert "installed local skills are the only specialist reference surface" in english_lower
    assert "readable `skill.md`" in english_lower
    assert "module_assignments" in english
    assert "runtime truth" in english_lower or "first truth surface" in english_lower
    assert (
        "without a new central catalog" in english_lower
        or "not a bigger central catalog" in english_lower
        or "without turning the product into a giant central catalog again" in english_lower
    )
    assert "external-first extension" not in english_lower
    assert "starter set" not in english_lower
    assert "local_first_skills" not in english_lower
    assert "not a claim" in english_lower and "final architecture" in english_lower
    assert "Local + starter Skills stay the product surface." not in english

    assert "已安装的本地 skill 根目录" in chinese
    assert "唯一专家来源" in chinese or "唯一 specialist 参考面" in chinese
    assert "SKILL.md" in chinese
    assert "module_assignments" in chinese
    assert "第一真相面" in chinese or "真相面" in chinese
    assert "不长出新的中心目录" in chinese or "不是更大的中心技能目录" in chinese
    assert "外部优先扩展" not in chinese
    assert "starter" not in chinese_lower
    assert "不是" in chinese and "最终架构已经完成" in chinese
    assert "本地 + starter Skills 仍然是默认产品面。" not in chinese


def test_quick_start_does_not_advertise_disabled_stage_labels() -> None:
    disabled_stage_labels = (
        "Vibe: What Do I Want?",
        "Vibe: How Do We Do It?",
        "Vibe: Do It",
    )
    for path in ("docs/quick-start.en.md", "docs/quick-start.md"):
        content = _read(path)
        for label in disabled_stage_labels:
            assert label not in content


def test_quick_start_points_normal_skill_extension_to_the_simple_install_docs() -> None:
    english = _read("docs/quick-start.en.md")
    chinese = _read("docs/quick-start.md")

    assert "local-first" not in english
    assert "declared local roots" in english or "local installed roots" in english
    assert "Custom Skills onboarding" not in english
    assert "custom-workflow-onboarding" not in english
    assert "install/README.en.md" in english

    assert "本地优先" not in chinese
    assert "已安装的本地 skill 根目录" in chinese
    assert "想接入自定义 Skills" not in chinese
    assert "custom-workflow-onboarding" not in chinese
    assert "install/README.md" in chinese


def test_simple_install_readmes_treat_pwsh_as_default_power_shell_surface() -> None:
    forbidden_phrases = (
        "must not be treated as the default prerequisite",
        "不要把 `pwsh` 当作默认前提",
    )
    for path in ("docs/install/README.en.md", "docs/install/README.md"):
        content = _read(path)
        assert "pwsh" in content
        assert "docs/install/prompts" not in content
        for phrase in forbidden_phrases:
            assert phrase not in content


def test_runtime_core_packaging_projections_do_not_track_local_repo_root() -> None:
    for path in (
        "config/runtime-core-packaging.full.json",
        "config/runtime-core-packaging.minimal.json",
    ):
        payload = json.loads(_read(path))
        assert "_repo_root" not in payload


def test_public_install_surfaces_point_to_skills_dir_installation() -> None:
    public_paths = (
        "README.md",
        "README.zh.md",
        "docs/install/README.en.md",
        "docs/install/README.md",
    )

    for path in public_paths:
        content = _read(path)
        assert "SkillsDir" in content or "--skills-dir" in content
        assert "skills/local" not in content
        assert "skills/custom/" not in content
        assert "custom-workflows.json" not in content


def test_install_readme_keeps_legacy_custom_workflow_onboarding_out_of_active_install_path() -> None:
    english = _read("docs/install/README.en.md")
    chinese = _read("docs/install/README.md")

    assert "Custom Skill onboarding" not in english
    assert "Advanced manifest-driven custom workflow onboarding" not in english
    assert "custom-workflow-onboarding.en.md" not in english
    assert "skill-roots.json" in english

    assert "自定义 Skill 接入" not in chinese
    assert "高级 manifest 驱动 custom workflow 接入" not in chinese
    assert "custom-workflow-onboarding.md" not in chinese
    assert "skill-roots.json" in chinese


def test_advanced_custom_workflow_doc_is_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/custom-workflow-onboarding.en.md",
        "docs/install/custom-workflow-onboarding.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_update_prompt_recipes_are_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/prompts/framework-only-update.en.md",
        "docs/install/prompts/framework-only-update.md",
        "docs/install/prompts/full-version-update.en.md",
        "docs/install/prompts/full-version-update.md",
    ):
        active_path = REPO_ROOT / path
        archived_path = (
            REPO_ROOT
            / "docs"
            / "archive"
            / "install-legacy"
            / "2026-07-02"
            / "prompts"
            / Path(path).name
        )
        assert not active_path.exists()
        assert archived_path.exists()


def test_custom_governance_rules_are_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/custom-skill-governance-rules.en.md",
        "docs/install/custom-skill-governance-rules.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_kernel_architecture_docs_describe_agent_led_binding_truth() -> None:
    architecture = _read("docs/architecture/local-agent-kernel-v2.md")
    interfaces = _read("docs/architecture/local-agent-kernel-v2-interfaces.md")
    architecture_lower = architecture.lower()
    interfaces_lower = interfaces.lower()

    assert "declared local skill roots are the only specialist reference surface" in architecture_lower
    assert "host-declared local roots are the only specialist reference surface" in interfaces_lower
    assert "external-first" not in architecture_lower
    assert "external-first" not in interfaces_lower
    assert "skills/local" not in architecture_lower
    assert "skills/local" not in interfaces_lower
    assert "module_assignments" in architecture
    expected_flow = "candidate discovery -> agent reads `skill.md` -> `agent_skill_organization` -> `module_assignments` -> execution"
    assert expected_flow in architecture_lower
    assert expected_flow in interfaces_lower
    assert "validated execution projection" in architecture_lower
    assert "validated execution projection" in interfaces_lower
    assert "planner preference is candidate audit only" in architecture_lower
    assert "planner preference is candidate audit only" in interfaces_lower
    assert "repo-owned" in architecture_lower and ("not the main extension story" in architecture_lower or "no repo-owned bundled corpus as the main extension surface" in architecture_lower)
    assert "skills-catalog.json" in interfaces
    assert "skills-index.json" in interfaces
    assert "--host-id" in interfaces
    assert "--workspace-root" in interfaces
    assert "provenance" in interfaces_lower
    assert "selected source" in interfaces_lower and "details" in interfaces_lower


def test_kernel_docs_keep_external_first_story_narrow_and_do_not_overclaim() -> None:
    readme = _read("README.md").lower()
    readme_zh = _read("README.zh.md")
    interfaces = _read("docs/architecture/local-agent-kernel-v2-interfaces.md").lower()

    assert re.search(
        r"(should not be described as|is not)\s+automatic orchestration of all installed skills",
        interfaces,
    )
    assert "not a claim" in readme and "final architecture" in readme
    assert "不是" in readme_zh and "最终架构已经完成" in readme_zh


def test_default_closure_docs_keep_small_proof_set_story() -> None:
    gate_index = _read("scripts/verify/gate-family-index.md")
    verify_readme = _read("scripts/verify/README.md")
    proof_bundle = _read("docs/status/non-regression-proof-bundle.md")
    readme = _read("README.md").lower()
    architecture = _read("docs/architecture/local-agent-kernel-v2.md").lower()

    assert "1. `vibe-governed-runtime-contract-gate.ps1`" in gate_index
    assert "5. `vibe-repo-cleanliness-gate.ps1`" in gate_index
    assert "10. `vibe-repo-cleanliness-gate.ps1`" not in gate_index
    assert "default closure should stay small" in gate_index.lower()
    assert 'vibe-governed-runtime-contract-gate.ps1' in verify_readme
    assert 'vibe-runtime-execution-proof-gate.ps1' in verify_readme
    assert 'vibe-governed-runtime-contract-gate.ps1' in proof_bundle
    assert 'vibe-runtime-execution-proof-gate.ps1' in proof_bundle
    assert 'Add-on audit commands are opt-in' in proof_bundle
    assert 'small default closure set + routing smoke + router contract' in proof_bundle
    assert 'vibe-current-routing-debt-gate.ps1' in proof_bundle
    assert 'Additional final regression checks stay outside the default closure gate set' in proof_bundle
    assert "normal closeout path should stay small" in readme
    assert "default closure story should stay small" in architecture


def test_public_readmes_keep_three_public_proof_layers_separate() -> None:
    english = _read("README.md")
    chinese = _read("README.zh.md")

    for content in (english, chinese):
        assert "`installed locally`" in content
        assert "`runtime coherent`" in content
        assert "`delivery accepted`" in content

    assert "current verification surface" not in english.lower()
    assert "当前验证入口" not in chinese


def test_runtime_protocol_maps_public_proof_layers_without_reintroducing_install_host_ready_states() -> None:
    protocol = _read("protocols/runtime.md")

    assert "`installed locally` belongs to install receipt / `check` and stays outside this protocol." in protocol
    assert "`runtime coherent` starts only after canonical entry returns a `session_root`" in protocol
    assert "`delivery accepted` is decided by the delivery-acceptance report" in protocol
    assert "vibe host-ready" not in protocol
    assert "online-ready" not in protocol


def test_active_runtime_docs_use_agent_skill_organization_as_skill_truth() -> None:
    english = _read("README.md")
    chinese = _read("README.zh.md")
    protocol = _read("protocols/runtime.md")
    team = _read("protocols/team.md")
    routing_contract = _read("docs/governance/current-routing-contract.md")
    field_contract = _read("docs/governance/current-runtime-field-contract.md")
    remediation = _read("docs/governance/built-in-skill-routing-remediation.md")

    for content in (english, chinese, protocol, team, routing_contract, field_contract):
        assert "agent_skill_organization" in content

    assert "route candidates are compatibility audit evidence only" in protocol
    assert "Agent-confirmed skill organization" in routing_contract
    assert "agent_skill_organization -> module-work-plan.json" in field_contract
    assert "module-work-plan.json -> agent-execution-handoff.json" in field_contract
    assert "agent-execution-handoff.json -> module-execution.json" in field_contract
    assert "Agent-led skill discovery cutover" in remediation
    assert "runtime 实际上已经由 router / canonical `vibe` 决定能力入口" not in remediation
    assert "eligible route candidates should auto-promote" not in protocol
    assert "route truth points at a selected skill" not in protocol
    assert "skill_candidates -> skill_routing.selected" not in routing_contract


def test_non_regression_proof_bundle_is_positioned_as_operator_closeout_contract() -> None:
    proof_bundle = _read("docs/status/non-regression-proof-bundle.md")

    assert "operator and contributor closeout contract" in proof_bundle
    assert "It is not the everyday public proof ladder" in proof_bundle
    assert "`installed locally` -> `check`" in proof_bundle
    assert "`runtime coherent` -> returned `session_root` truth artifacts" in proof_bundle
    assert "`delivery accepted` -> delivery-acceptance report" in proof_bundle


def test_manifest_driven_custom_governance_doc_is_legacy_archive_only() -> None:
    for path in (
        "docs/install/custom-skill-governance-rules.en.md",
        "docs/install/custom-skill-governance-rules.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_framework_only_reference_pages_are_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/framework-only-path.en.md",
        "docs/install/framework-only-path.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_installation_rules_and_minimal_path_are_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/installation-rules.en.md",
        "docs/install/installation-rules.md",
        "docs/install/minimal-path.en.md",
        "docs/install/minimal-path.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_recommended_full_and_enterprise_reference_pages_are_archived_not_active_install_guidance() -> None:
    for path in (
        "docs/install/recommended-full-path.en.md",
        "docs/install/enterprise-governed-path.en.md",
        "docs/install/recommended-full-path.md",
        "docs/install/enterprise-governed-path.md",
    ):
        assert not (REPO_ROOT / path).exists()
        assert (REPO_ROOT / "docs" / "archive" / "install-legacy" / "2026-07-02" / Path(path).name).exists()


def test_opencode_reference_page_is_archived_not_active_install_guidance() -> None:
    active_note = REPO_ROOT / "docs/install/opencode-path.en.md"
    archived_note = REPO_ROOT / "docs/archive/install-legacy/2026-07-02/opencode-path.en.md"
    archived_cn_note = REPO_ROOT / "docs/archive/install-legacy/2026-07-02/opencode-path.md"

    assert not active_note.exists()
    assert archived_note.exists()
    assert archived_cn_note.exists()
    assert not (REPO_ROOT / "docs/install/opencode-path.md").exists()
