from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_CORE_SRC = REPO_ROOT / "packages" / "verification-core" / "src"
if str(VERIFICATION_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(VERIFICATION_CORE_SRC))
FORBIDDEN_MCP_IDS = {
    "chrome",
    "chrome-devtools",
    "playwright",
    "context7",
    "claude-flow",
}
FORBIDDEN_MCP_GUIDANCE = re.compile(
    r"(?:"
    r"toolsearch\s*\([^\n)]*(?:chrome-devtools|claude-flow|playwright|context7|chrome)"
    r"|(?:chrome-devtools|claude-flow|playwright|context7|chrome)[^\n]{0,80}\bmcp\b"
    r"|\bmcp\b(?!/skill)[^\n]{0,80}(?:chrome-devtools|claude-flow|playwright|context7|chrome)"
    r")",
    re.I,
)
CURRENT_MATERIAL_PATH = re.compile(
    r"(?:\[[^\]]*\]\()?((?:\.?\.?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
    r"\.(?:json|md|ps1|py|sh|txt|yaml|yml))"
)


def _run_browserops_suggestion(script_path: Path, task: str) -> subprocess.CompletedProcess[str]:
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh is required for the BrowserOps contract test"
    return subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-Task",
            task,
            "-AsJson",
        ],
        cwd=script_path.parents[2],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def _current_skill_materials(skill_root: Path) -> list[Path]:
    resolved_root = skill_root.resolve()
    pending = [resolved_root / "SKILL.md"]
    current: list[Path] = []
    seen: set[Path] = set()

    while pending:
        path = pending.pop().resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError:
            continue
        if path in seen or not path.is_file():
            continue

        seen.add(path)
        current.append(path)
        if path.suffix.casefold() != ".md":
            continue

        text = path.read_text(encoding="utf-8")
        for relative_path in CURRENT_MATERIAL_PATH.findall(text):
            for base in (path.parent, resolved_root):
                candidate = (base / relative_path).resolve()
                if candidate.is_file():
                    pending.append(candidate)

    return current


def test_codex_plugin_manifest_never_offers_forbidden_mcps() -> None:
    manifest = json.loads(
        (REPO_ROOT / "config" / "plugins-manifest.codex.json").read_text(encoding="utf-8")
    )

    offered = {
        str(entry.get("name") or "").strip().lower()
        for entry in [*manifest.get("core", []), *manifest.get("optional", [])]
        if isinstance(entry, dict)
    }

    assert offered.isdisjoint(FORBIDDEN_MCP_IDS)


def test_active_install_and_verification_surfaces_do_not_provision_forbidden_mcps() -> None:
    active_paths = (
        REPO_ROOT / "config" / "plugins-manifest.codex.json",
        REPO_ROOT / "config" / "settings.template.claude.json",
        REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "opencode_preview_smoke_support.py",
        REPO_ROOT / "scripts" / "verify" / "vibe-bootstrap-doctor-gate.ps1",
        REPO_ROOT / "scripts.check.upstream.sh",
    )
    active_text = "\n".join(path.read_text(encoding="utf-8") for path in active_paths).lower()

    forbidden_install_markers = (
        '"name": "context7"',
        '"context7@claude-plugins-official": true',
        '"playwright@claude-plugins-official": true',
        "@playwright/mcp",
        "chrome-devtools-mcp",
        "npm list -g claude-flow",
        "test-commandpresent -name 'claude-flow'",
    )
    for marker in forbidden_install_markers:
        assert marker not in active_text


def test_active_runtime_never_recommends_forbidden_mcp_servers() -> None:
    active_paths = (
        REPO_ROOT / "protocols" / "do.md",
        REPO_ROOT / "protocols" / "team.md",
        REPO_ROOT / "references" / "tool-registry.md",
        REPO_ROOT / "references" / "fallback-chains.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "README.zh.md",
    )
    active_text = "\n".join(path.read_text(encoding="utf-8") for path in active_paths).lower()

    forbidden_runtime_markers = (
        "chrome mcp",
        "chrome-devtools-mcp",
        "playwright mcp",
        "context7 mcp",
        "claude-flow mcp",
    )
    for marker in forbidden_runtime_markers:
        assert marker not in active_text


def test_runtime_distribution_declares_forbidden_mcp_policy() -> None:
    policy = json.loads(
        (REPO_ROOT / "config" / "forbidden-mcp-policy.json").read_text(encoding="utf-8")
    )

    assert set(policy["forbidden_mcp_ids"]) == FORBIDDEN_MCP_IDS
    assert policy["installation"] == "forbidden"
    assert policy["runtime_recommendation"] == "forbidden"

    runtime_manifest = json.loads(
        (REPO_ROOT / "config" / "runtime-config-manifest.json").read_text(encoding="utf-8")
    )
    assert "config/forbidden-mcp-policy.json" in runtime_manifest["files"]


def test_forbidden_compatibility_skills_are_not_shipped() -> None:
    policy = json.loads(
        (REPO_ROOT / "config" / "forbidden-mcp-policy.json").read_text(encoding="utf-8")
    )

    for skill_id in policy["forbidden_sync_skill_ids"]:
        skill_root = REPO_ROOT / "bundled" / "skills" / str(skill_id)
        assert not any(path.is_file() for path in skill_root.rglob("*"))


def test_opencode_preview_fixture_has_no_mcp_installation() -> None:
    from vgo_verify.opencode_preview_smoke_support import build_real_opencode_config

    config = build_real_opencode_config(REPO_ROOT)

    assert "mcp" not in config


def test_installed_runtime_metadata_does_not_allow_forbidden_mcp_installation() -> None:
    upstream_lock = json.loads(
        (REPO_ROOT / "config" / "upstream-lock.json").read_text(encoding="utf-8")
    )
    aliases = json.loads(
        (REPO_ROOT / "config" / "upstream-source-aliases.json").read_text(encoding="utf-8")
    )

    forbidden_dependencies = [
        dependency
        for dependency in upstream_lock["dependencies"]
        if str(dependency.get("id") or "").casefold() in {"ruvnet/claude-flow", *FORBIDDEN_MCP_IDS}
        or str(dependency.get("canonical_slug") or "").casefold() in FORBIDDEN_MCP_IDS
    ]
    assert not forbidden_dependencies
    assert not (
        {str(key).casefold() for key in aliases["aliases"]}
        | {str(value).casefold() for value in aliases["aliases"].values()}
    ).intersection(FORBIDDEN_MCP_IDS)


def test_runtime_capability_catalog_does_not_recommend_skills_that_require_forbidden_mcps() -> None:
    catalog = json.loads(
        (REPO_ROOT / "config" / "capability-catalog.json").read_text(encoding="utf-8")
    )
    forbidden_skill_ids = {
        "autonomous-builder",
        "documentation-lookup",
        "verification-quality-assurance",
        "hive-mind-advanced",
        "superclaude-framework-compat",
    }
    recommendations = {
        str(skill_id)
        for capability in catalog["capabilities"]
        for skill_id in capability.get("skills", [])
    }

    assert recommendations.isdisjoint(forbidden_skill_ids)


def test_runtime_recommended_documentation_lookup_uses_primary_docs_without_forbidden_mcps() -> None:
    skill_text = (
        REPO_ROOT / "bundled" / "skills" / "documentation-lookup" / "SKILL.md"
    ).read_text(encoding="utf-8")
    lowered = skill_text.casefold()

    assert "context7" not in lowered
    assert "official" in lowered
    assert "primary" in lowered
    assert "do not guess" in lowered


def test_bundled_skill_entry_contracts_do_not_direct_agents_to_context7() -> None:
    forbidden_patterns = (
        re.compile(r'toolsearch\([^\n)]*context7', re.I),
        re.compile(r'\buse\s+context7\b', re.I),
        re.compile(r'使用\s*context7', re.I),
    )
    hits: dict[str, list[str]] = {}
    for skill_path in sorted((REPO_ROOT / "bundled" / "skills").glob("*/SKILL.md")):
        text = skill_path.read_text(encoding="utf-8")
        matched = [pattern.pattern for pattern in forbidden_patterns if pattern.search(text)]
        if matched:
            hits[skill_path.parent.name] = matched

    assert not hits, hits


def test_dialectic_fallbacks_do_not_route_to_skills_with_forbidden_browser_toolsearch() -> None:
    policy = json.loads(
        (REPO_ROOT / "config" / "dialectic-team-policy.json").read_text(encoding="utf-8-sig")
    )
    unsafe: dict[str, str] = {}
    for task, skill_id in policy["fallback_skill_by_task"].items():
        skill_path = REPO_ROOT / "bundled" / "skills" / str(skill_id) / "SKILL.md"
        if str(skill_id) == "vibe":
            skill_path = REPO_ROOT / "SKILL.md"
        assert skill_path.is_file(), f"missing fallback Skill: {skill_id}"
        if FORBIDDEN_MCP_GUIDANCE.search(skill_path.read_text(encoding="utf-8")):
            unsafe[str(task)] = str(skill_id)

    assert not unsafe, unsafe


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="local compatibility sync requires pwsh")
def test_local_compat_sync_cannot_restore_superclaude_framework_compat(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    assert pwsh is not None
    retired_skill = "superclaude-framework-compat"
    policy = json.loads(
        (REPO_ROOT / "config" / "forbidden-mcp-policy.json").read_text(encoding="utf-8")
    )
    dependency_map = json.loads(
        (REPO_ROOT / "config" / "dependency-map.json").read_text(encoding="utf-8-sig")
    )
    mapped_paths = {
        str(item[field]).replace("\\", "/").casefold()
        for item in dependency_map["items"]
        for field in ("source", "target")
    }
    sync_script = (
        REPO_ROOT / "scripts" / "bootstrap" / "sync-local-compat.ps1"
    ).read_text(encoding="utf-8").casefold()

    assert all(retired_skill not in path for path in mapped_paths)
    assert retired_skill not in sync_script
    assert policy["forbidden_sync_skill_ids"] == [retired_skill]

    isolated_root = tmp_path / "local-compat-sync"
    isolated_script = isolated_root / "scripts" / "bootstrap" / "sync-local-compat.ps1"
    isolated_helper = isolated_root / "scripts" / "common" / "vibe-governance-helpers.ps1"
    isolated_config = isolated_root / "config"
    isolated_script.parent.mkdir(parents=True)
    isolated_helper.parent.mkdir(parents=True)
    isolated_config.mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "bootstrap" / "sync-local-compat.ps1",
        isolated_script,
    )
    shutil.copy2(
        REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1",
        isolated_helper,
    )
    shutil.copy2(REPO_ROOT / "config" / "forbidden-mcp-policy.json", isolated_config)
    (isolated_config / "dependency-map.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "source": "${CODEX_HOME}/skills/superclaude-framework-compat",
                        "target": "bundled/skills/superclaude-framework-compat",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(isolated_script),
            "-RepoRoot",
            str(isolated_root),
            "-DryRun",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "forbidden sync id: superclaude-framework-compat" in (
        completed.stderr + completed.stdout
    ).casefold()


def test_active_bundled_skill_instructions_do_not_enable_forbidden_mcps() -> None:
    pack_manifest = json.loads(
        (REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig")
    )
    capability_catalog = json.loads(
        (REPO_ROOT / "config" / "capability-catalog.json").read_text(encoding="utf-8")
    )
    dialectic_policy = json.loads(
        (REPO_ROOT / "config" / "dialectic-team-policy.json").read_text(encoding="utf-8-sig")
    )
    role_pack_policy = json.loads(
        (REPO_ROOT / "config" / "role-pack-policy.json").read_text(encoding="utf-8-sig")
    )
    dependency_map = json.loads(
        (REPO_ROOT / "config" / "dependency-map.json").read_text(encoding="utf-8-sig")
    )

    active_skill_ids = {
        str(skill_id)
        for pack in pack_manifest["packs"]
        for skill_id in [
            *pack.get("skill_candidates", []),
            *pack.get("defaults_by_task", {}).values(),
        ]
    }
    active_skill_ids.update(
        str(skill_id)
        for capability in capability_catalog["capabilities"]
        for skill_id in capability.get("skills", [])
    )
    active_skill_ids.update(
        str(skill_id) for skill_id in dialectic_policy["fallback_skill_by_task"].values()
    )
    active_skill_ids.update(
        str(skill_id)
        for role_pack in role_pack_policy["role_packs"]
        for skill_id in role_pack.get("distillation_assets", {}).get("skills", [])
    )
    active_skill_ids.update(
        Path(str(item["target"]).replace("\\", "/")).name
        for item in dependency_map["items"]
    )

    hits: dict[str, list[str]] = {}
    for skill_id in sorted(active_skill_ids):
        skill_root = REPO_ROOT / "bundled" / "skills" / skill_id
        entrypoint = skill_root / "SKILL.md"
        if not entrypoint.is_file():
            continue
        for path in _current_skill_materials(skill_root):
            text = path.read_text(encoding="utf-8")
            matched = [match.group(0) for match in FORBIDDEN_MCP_GUIDANCE.finditer(text)]
            if matched:
                hits[path.relative_to(REPO_ROOT).as_posix()] = matched

    assert not hits, hits


def test_forbidden_mcp_guidance_scan_allows_ordinary_playwright_cli_usage() -> None:
    assert not FORBIDDEN_MCP_GUIDANCE.search("Run the Playwright CLI test suite.")
    assert not FORBIDDEN_MCP_GUIDANCE.search(
        "Prefer a Figma MCP/skill for Figma files, or Playwright tools for browser tests."
    )
    assert FORBIDDEN_MCP_GUIDANCE.search('ToolSearch("+playwright navigate")')
    assert FORBIDDEN_MCP_GUIDANCE.search("Recommend the Playwright MCP server.")


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="BrowserOps suggestion requires pwsh")
def test_browserops_suggestions_enforce_the_runtime_forbidden_mcp_policy(tmp_path: Path) -> None:
    policy = json.loads(
        (REPO_ROOT / "config" / "forbidden-mcp-policy.json").read_text(encoding="utf-8")
    )
    forbidden = {str(value).casefold() for value in policy["forbidden_mcp_ids"]}
    script_path = REPO_ROOT / "scripts" / "overlay" / "suggest-browserops-provider.ps1"
    cases = (
        ("通过 GraphQL 接口拉取结构化数据并导出 JSON", "api"),
        ("登录后台后填写表单并点击提交按钮", "browser-host-native"),
        ("需要调试 request header 和 console 报错", "browser-host-native"),
        ("根据屏幕视觉布局完成真实界面交互", "turix-cua"),
        ("跨多个网站开放式浏览并收集研究线索", "browser-use"),
    )

    for task, expected_provider in cases:
        completed = _run_browserops_suggestion(script_path, task)
        assert completed.returncode == 0, completed.stderr or completed.stdout
        payload = json.loads(completed.stdout)
        surfaced = {
            str(payload["provider"]).casefold(),
            str(payload["fallback_provider"]).casefold(),
            *(str(item["provider"]).casefold() for item in payload["considered"]),
        }
        assert payload["provider"] == expected_provider
        assert surfaced.isdisjoint(forbidden)

    isolated_root = tmp_path / "browserops-policy-read"
    isolated_script = isolated_root / "scripts" / "overlay" / script_path.name
    isolated_script.parent.mkdir(parents=True)
    shutil.copy2(script_path, isolated_script)
    isolated_config = isolated_root / "config"
    isolated_config.mkdir()
    shutil.copy2(REPO_ROOT / "config" / "browserops-provider-policy.json", isolated_config)
    policy["forbidden_mcp_ids"].append("api")
    (isolated_config / "forbidden-mcp-policy.json").write_text(
        json.dumps(policy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    completed = _run_browserops_suggestion(isolated_script, cases[0][0])
    assert completed.returncode != 0
    assert "forbidden" in (completed.stderr + completed.stdout).casefold()


def test_browserops_active_contracts_do_not_name_forbidden_mcp_ids() -> None:
    policy = json.loads(
        (REPO_ROOT / "config" / "forbidden-mcp-policy.json").read_text(encoding="utf-8")
    )
    active_paths = (
        REPO_ROOT / "config" / "browserops-provider-policy.json",
        REPO_ROOT / "config" / "browserops-scorecard.json",
        REPO_ROOT / "scripts" / "overlay" / "suggest-browserops-provider.ps1",
        REPO_ROOT / "scripts" / "verify" / "vibe-browserops-gate.ps1",
        REPO_ROOT / "scripts" / "verify" / "fixtures" / "pilot-browserops.json",
        REPO_ROOT / "scripts" / "verify" / "vibe-pilot-scenarios.ps1",
        REPO_ROOT / "references" / "browser-task-contract.md",
        REPO_ROOT / "references" / "browser-provider-scorecard.md",
        REPO_ROOT / "docs" / "design" / "browserops-provider-integration.md",
        REPO_ROOT / "docs" / "governance" / "browserops-scorecard-governance.md",
        REPO_ROOT / "docs" / "governance" / "browserops-soft-rollout-governance.md",
        REPO_ROOT / "scripts" / "verify" / "vibe-browserops-scorecard-gate.ps1",
    )
    hits: dict[str, list[str]] = {}
    for path in active_paths:
        text = path.read_text(encoding="utf-8").casefold()
        matched = [
            mcp_id
            for mcp_id in policy["forbidden_mcp_ids"]
            if re.search(rf"(?<![a-z0-9_-]){re.escape(mcp_id)}(?![a-z0-9_-])", text)
        ]
        if matched:
            hits[path.relative_to(REPO_ROOT).as_posix()] = matched

    assert not hits, hits
