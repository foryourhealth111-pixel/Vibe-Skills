from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages/runtime-core/src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.skill_authority import resolve_skill_authority, skill_root_projection


@pytest.fixture
def source_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    target = home / ".agents"
    workspace = tmp_path / "workspace"
    (target / "skills").mkdir(parents=True)
    workspace.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home, target, workspace


def _skill(root: Path, skill_id: str = "report", *, enabled: bool = True) -> Path:
    path = root / skill_id / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {skill_id}\ndescription: Write a report.\nenabled: {str(enabled).lower()}\n---\n# Report\n",
        encoding="utf-8",
    )
    return path


def _authority(target: Path, workspace: Path, skill_id: str = "report", **kwargs):
    return resolve_skill_authority(
        repo_root=REPO_ROOT, agent_root=target, host_id="codex", workspace_root=workspace,
        skill_id=skill_id, **kwargs,
    )


def test_skill_authority_reads_current_source_identity_without_writing_caches(source_environment) -> None:
    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    before = set(home.rglob("*"))
    authority = _authority(target, workspace)
    assert authority["valid"] is True
    assert authority["canonical_entrypoint"] == str(descriptor.resolve())
    assert authority["content_sha256"] == hashlib.sha256(descriptor.read_bytes()).hexdigest()
    assert authority["description"] == "Write a report."
    assert set(home.rglob("*")) == before
    descriptor.write_text(descriptor.read_text(encoding="utf-8") + "New instructions.\n", encoding="utf-8")
    refreshed = _authority(target, workspace)
    assert refreshed["content_sha256"] != authority["content_sha256"]
    assert set(home.rglob("*")) == before


@pytest.mark.parametrize("identity", ["", ".", "..", "../report", "..\\report", "/report", "C:report", "vibe", "VIBE"])
def test_skill_authority_rejects_nonlocal_identifiers_and_controller_aliases(source_environment, identity: str) -> None:
    home, target, workspace = source_environment
    _skill(home)
    assert _authority(target, workspace, identity)["valid"] is False


@pytest.mark.parametrize("scope", ["user", "workspace"])
def test_skill_authority_resolves_configured_roots_and_reports_the_same_guide_order(source_environment, scope: str) -> None:
    home, target, workspace = source_environment
    root = workspace / "team skills"
    descriptor = _skill(root)
    config = (home if scope == "user" else workspace) / ".vibeskills/skill-roots.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(root)]}), encoding="utf-8")
    authority = _authority(target, workspace)
    assert authority["canonical_entrypoint"] == str(descriptor.resolve())
    assert authority["source_priority"] == 0
    assert skill_root_projection(
        repo_root=REPO_ROOT, agent_root=target, host_id="codex", workspace_root=workspace,
    )[0] == {"kind": scope + "_extra", "path": str(root.resolve())}


def test_disabled_higher_precedence_skill_shadows_an_enabled_duplicate(source_environment) -> None:
    home, target, workspace = source_environment
    root = workspace / "team skills"
    _skill(root, enabled=False)
    _skill(target / "skills")
    config = workspace / ".vibeskills/skill-roots.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(root)]}), encoding="utf-8")
    result = _authority(target, workspace)
    assert result["valid"] is False
    assert result["reason"] == "skill_disabled"


def test_skill_authority_resolves_unique_plugin_sources_and_rejects_ambiguous_versions(source_environment) -> None:
    home, target, workspace = source_environment
    cache = home / ".codex/plugins/cache"
    descriptor = _skill(cache / "provider/documents/1/skills")
    assert _authority(target, workspace)["canonical_entrypoint"] == str(descriptor.resolve())
    _skill(cache / "provider/documents/2/skills")
    result = _authority(target, workspace)
    assert result["valid"] is False
    assert result["reason"] == "ambiguous_nested_skill_id"


@pytest.mark.parametrize("provided", ["matching", "missing", "foreign"])
def test_skill_authority_validates_provided_entrypoint_identity(source_environment, provided: str) -> None:
    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    entrypoint = str(descriptor) if provided == "matching" else None if provided == "missing" else str(_skill(home))
    result = _authority(target, workspace, skill_entrypoint=entrypoint, require_provided_entrypoint=True)
    assert result["valid"] is (provided == "matching")
    assert result["canonical_entrypoint"] == str(descriptor.resolve())


@pytest.mark.parametrize("destination", ["outside", "controller"])
def test_skill_authority_rejects_symlinked_outside_sources_and_controller_aliases(source_environment, destination: str) -> None:
    home, target, workspace = source_environment
    external = _skill(home) if destination == "outside" else _skill(target / "skills", "vibe")
    link = target / "skills/report"
    try:
        link.symlink_to(external.parent, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink creation is unavailable: {exc}")
    assert _authority(target, workspace)["valid"] is False


def test_unreadable_unrelated_skill_does_not_hide_a_valid_selected_source(source_environment, monkeypatch: pytest.MonkeyPatch) -> None:
    home, target, workspace = source_environment
    valid = _skill(target / "skills")
    unreadable = _skill(target / "skills", "unreadable")
    read_bytes = Path.read_bytes

    def read(path: Path) -> bytes:
        if path == unreadable:
            raise PermissionError("test source is unreadable")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    assert _authority(target, workspace)["canonical_entrypoint"] == str(valid.resolve())
    result = _authority(target, workspace, "unreadable")
    assert result["valid"] is False
    assert result["reason"] == "unreadable_skill_md"


@pytest.mark.parametrize("custom_kind", ["absent", "directory", "file"])
def test_unrelated_custom_entry_preserves_valid_skills(source_environment, custom_kind: str) -> None:
    from vgo_runtime.kernel.skill_index import scan_skill_catalog

    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    custom = target / "skills/custom"
    if custom_kind == "directory":
        custom.mkdir()
    elif custom_kind == "file":
        custom.write_text("Unrelated local file.\n", encoding="utf-8")
    catalog = scan_skill_catalog(agent_root=target, host_roots=(target / "skills",))
    assert [row["skill_id"] for row in catalog["entries"] if row["active"]] == ["report"]
    assert _authority(target, workspace)["canonical_entrypoint"] == str(descriptor.resolve())


def test_controller_descriptor_alias_cannot_shadow_a_valid_skill(source_environment) -> None:
    from vgo_runtime.kernel.skill_index import scan_skill_catalog

    home, target, workspace = source_environment
    controller = _skill(target / "skills", "vibe")
    alias = target / "skills/report/SKILL.md"
    alias.parent.mkdir()
    try:
        alias.symlink_to(controller)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"File symlink creation is unavailable: {exc}")
    lower_root = workspace / "lower-skills"
    valid = _skill(lower_root)
    config = workspace / ".vibeskills/skill-roots.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(target / "skills"), str(lower_root)]}), encoding="utf-8")
    catalog = scan_skill_catalog(agent_root=target, host_roots=(target / "skills", lower_root))
    assert [row["resolved_skill_file"] for row in catalog["entries"] if row["active"]] == [str(valid.resolve())]
    assert _authority(target, workspace)["canonical_entrypoint"] == str(valid.resolve())


@pytest.mark.parametrize("requested", [False, True])
def test_candidate_audit_preserves_disabled_source_rejection(source_environment, requested: bool) -> None:
    from vgo_runtime.router_contract_runtime import route_prompt

    home, target, workspace = source_environment
    disabled_root = workspace / "disabled-skills"
    _skill(disabled_root, enabled=False)
    _skill(target / "skills")
    config = workspace / ".vibeskills/skill-roots.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(disabled_root)]}), encoding="utf-8")
    result = route_prompt(
        prompt="Write a report.", grade="L", task_type="writing", repo_root=REPO_ROOT,
        target_root=target, host_id="codex", workspace_root=workspace,
        requested_skill="report" if requested else None,
    )
    assert _authority(target, workspace)["reason"] == "skill_disabled"
    assert result.get("candidate_focus") is None or result["candidate_focus"]["authority"]["eligible"] is False
    rows = [row for row in result["candidates"] if row["skill"] == "report"]
    assert rows and all(row["authority_eligible"] is False for row in rows)
    assert all("skill_disabled" in row["authority_rejection_reasons"] for row in rows)


@pytest.mark.parametrize("requested", ["report", "missing-skill", None])
def test_explicit_rejected_skill_cannot_fall_through_to_composite_selection(source_environment, requested: str | None) -> None:
    from vgo_runtime.router_contract_runtime import route_prompt

    home, target, workspace = source_environment
    _skill(target / "skills", enabled=False)
    for identity, capability, description in (
        ("source-digger", "research.literature_search", "Search primary literature and PubMed evidence."),
        ("helpful-briefer", "writing.reader_report", "Turn technical material into plain-language summaries for ordinary readers."),
        ("slide-craft", "presentation.deck", "Prepare presentation slides and deck outputs."),
    ):
        descriptor = _skill(target / "skills", identity)
        descriptor.write_text(
            f"---\nname: {identity}\ndescription: {description}\ncapabilities:\n  - {capability}\n---\n",
            encoding="utf-8",
        )
    result = route_prompt(
        prompt="先检索 PubMed 和 primary literature，再写一份给普通读者看的通俗 brief，最后整理成 slides。",
        grade="XL", task_type="research", repo_root=REPO_ROOT,
        target_root=target, host_id="codex", workspace_root=workspace, requested_skill=requested,
    )
    assert len([row for row in result["skill_routing"]["module_candidates"] if row["candidates"]]) >= 2
    if requested is None:
        assert result["candidate_focus"] is not None
        assert result["skill_routing"]["focused_candidates"]
    else:
        assert result["candidate_focus"] is None
        assert result["skill_routing"]["focused_candidates"] == []
        expected_reason = "requested_local_skill_ineligible" if requested == "report" else "requested_local_skill_not_found"
        assert result["route_reason"] == expected_reason
        if requested == "report":
            rows = [row for row in result["candidates"] if row["skill"] == "report"]
            assert rows and all("skill_disabled" in row["authority_rejection_reasons"] for row in rows)


@pytest.mark.parametrize("requested", [False, True])
def test_candidate_audit_rejects_sources_outside_canonical_admission(source_environment, requested: bool) -> None:
    from vgo_runtime.router_contract_runtime import route_prompt

    home, target, workspace = source_environment
    _skill(target / "vibe/skills/local")
    authority = _authority(target, workspace)
    result = route_prompt(
        prompt="Write a report.", grade="L", task_type="writing", repo_root=REPO_ROOT,
        target_root=target, host_id="codex", workspace_root=workspace,
        requested_skill="report" if requested else None,
    )
    assert authority["valid"] is False
    rows = [row for row in result["candidates"] if row["skill"] == "report"]
    assert rows and all(row["authority_eligible"] is False for row in rows)
    assert all(authority["reason"] in row["authority_rejection_reasons"] for row in rows)
    assert result.get("candidate_focus") is None or result["candidate_focus"]["authority"]["eligible"] is False


@pytest.mark.parametrize("host_id,expected", [("claude-code", True), ("claude", True), (" CLAUDE ", True), ("codex", False)])
def test_directory_name_default_is_scoped_to_claude_sources(source_environment, host_id: str, expected: bool) -> None:
    home, target, workspace = source_environment
    skill = _skill(target / "skills")
    skill.write_text("---\ndescription: Write a report.\n---\n# Report\n", encoding="utf-8")
    authority = resolve_skill_authority(
        repo_root=REPO_ROOT, agent_root=target, host_id=host_id,
        workspace_root=workspace, skill_id="report",
    )
    assert authority["valid"] is expected
    if expected:
        assert authority["canonical_entrypoint"] == str(skill.resolve())
    else:
        assert authority["reason"] == "missing_required_frontmatter"


@pytest.mark.parametrize("value", ["''", "42", "true", "[]"])
def test_claude_name_default_does_not_replace_invalid_explicit_names(source_environment, value: str) -> None:
    home, target, workspace = source_environment
    skill = _skill(target / "skills")
    skill.write_text(f"---\nname: {value}\ndescription: Write a report.\n---\n", encoding="utf-8")
    authority = resolve_skill_authority(
        repo_root=REPO_ROOT, agent_root=target, host_id="claude-code",
        workspace_root=workspace, skill_id="report",
    )
    assert authority["valid"] is False


def test_authority_batch_shares_one_catalog_without_writing_cache(source_environment, monkeypatch: pytest.MonkeyPatch) -> None:
    from vgo_runtime import skill_authority

    home, target, workspace = source_environment
    for skill_id in ("report", "summary", "unused"):
        descriptor = _skill(target / "skills", skill_id)
        (descriptor.parent / "resource.bin").write_bytes(b"resource contents")
    requests = [{"skill_id": "report"}, {"skill_id": "summary"}, {"skill_id": "report"}, {"skill_id": "missing"}]
    expected = [_authority(target, workspace, row["skill_id"]) for row in requests]
    before = set(home.rglob("*"))
    original_open = Path.open
    reads = []

    def count_resources(path, *args, **kwargs):
        if path.name == "resource.bin":
            reads.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", count_resources)
    actual = skill_authority.resolve_skill_authorities(
        repo_root=REPO_ROOT, agent_root=target, host_id="codex",
        workspace_root=workspace, requests=requests,
    )
    assert actual == expected
    assert len(reads) == 3
    assert set(home.rglob("*")) == before
    assert not (target / "vibe/generated").exists()


def test_authority_batch_revalidates_the_next_request(source_environment) -> None:
    from vgo_runtime import skill_authority

    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    arguments = dict(repo_root=REPO_ROOT, agent_root=target, host_id="codex", workspace_root=workspace, requests=[{"skill_id": "report"}])
    first = skill_authority.resolve_skill_authorities(**arguments)
    descriptor.write_text(descriptor.read_text(encoding="utf-8") + "Updated instructions.\n", encoding="utf-8")
    second = skill_authority.resolve_skill_authorities(**arguments)
    assert second[0]["valid"] is True
    assert second[0]["content_sha256"] != first[0]["content_sha256"]


@pytest.mark.parametrize("requests", [{"skill_id": "report"}, ["report"], [{"skill_id": 1}], [{"skill_id": "report", "extra": True}], [{"skill_id": "report", "require_provided_entrypoint": "false"}]])
def test_authority_batch_rejects_malformed_requests(source_environment, requests: object) -> None:
    from vgo_runtime import skill_authority

    home, target, workspace = source_environment
    with pytest.raises(ValueError, match="request"):
        skill_authority.resolve_skill_authorities(
            repo_root=REPO_ROOT, agent_root=target, host_id="codex",
            workspace_root=workspace, requests=requests,
        )


def test_authority_batch_cli_preserves_entrypoint_checks_and_order(source_environment, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from vgo_runtime import skill_authority

    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    request_file = tmp_path / "requests with spaces.json"
    request_file.write_text(json.dumps([
        {"skill_id": "report", "skill_entrypoint": str(descriptor), "require_provided_entrypoint": True},
        {"skill_id": "report", "skill_entrypoint": str(tmp_path / "other/SKILL.md")},
        {"skill_id": "report", "require_provided_entrypoint": True},
        {"skill_id": "missing"},
    ]), encoding="utf-8")
    assert skill_authority.main([
        "--repo-root", str(REPO_ROOT), "--agent-root", str(target), "--host-id", "codex",
        "--workspace-root", str(workspace), "--requests-json-file", str(request_file),
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["reason"] for row in payload["authorities"]] == ["ok", "entrypoint_mismatch", "missing_skill_entrypoint", "not_in_local_skill_index"]


def test_powershell_dispatch_batches_identity_checks_and_rechecks_changes(source_environment, tmp_path: Path) -> None:
    import shutil
    import subprocess

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell executable not available")
    home, target, workspace = source_environment
    descriptor = _skill(target / "skills")
    units = [{
        "unit_id": f"unit-{index}", "module_id": "reporting", "skill_id": "report",
        "skill_entrypoint": str(descriptor), "content_sha256": hashlib.sha256(descriptor.read_bytes()).hexdigest(),
        "depends_on_unit_ids": [], "phase_id": "write", "stage_order": index,
        "responsibility": "Produce a report.", "role": "owner", "write_scope": "outputs",
        "expected_outputs": ["report.md"], "verification": ["Check the report."],
    } for index in range(3)]
    plan = tmp_path / "dispatch-plan.json"
    plan.write_text(json.dumps({"workflow_level": "L", "work_units": units}), encoding="utf-8")
    def quote(value: object) -> str:
        return "'" + str(value).replace("'", "''") + "'"
    command = (
        f". {quote(REPO_ROOT / 'scripts/runtime/VibeRuntime.Common.ps1')}; "
        "$script:authorityPythonSpec = Get-VgoPythonCommand; $script:authorityCalls = 0; "
        "function Get-VgoPythonCommand { $script:authorityCalls++; return $script:authorityPythonSpec }; "
        f"$plan = Get-Content -LiteralPath {quote(plan)} -Raw -Encoding UTF8 | ConvertFrom-Json; "
        f"$arguments = @{{ModuleWorkPlan=$plan; RepoRoot={quote(REPO_ROOT)}; TargetRoot={quote(target)}; HostId='codex'; WorkspaceRoot={quote(workspace)}}}; "
        "$rows = @(Convert-VibeModuleWorkPlanToDispatch @arguments); "
        f"[System.IO.File]::AppendAllText({quote(descriptor)}, 'Changed instructions.'); "
        "$rejected = $false; try { Convert-VibeModuleWorkPlanToDispatch @arguments | Out-Null } "
        "catch { if ($_.Exception.Message -notmatch 'skill_content_changed') { throw }; $rejected = $true }; "
        "[pscustomobject]@{ count=$rows.Count; calls=$script:authorityCalls; rejected=$rejected; units=@($rows.work_unit_id) } | ConvertTo-Json -Compress"
    )
    result = subprocess.run([shell, "-NoLogo", "-NoProfile", "-Command", command], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"count": 3, "calls": 2, "rejected": True, "units": ["unit-0", "unit-1", "unit-2"]}
