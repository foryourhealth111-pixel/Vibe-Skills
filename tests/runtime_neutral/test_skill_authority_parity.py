from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.runtime_neutral.test_agent_skill_organization_contract import (
    REPO_ROOT,
    agent_direct_organization,
    resolve_powershell,
    run_freeze,
)


RUNTIME_SRC = REPO_ROOT / "packages/runtime-core/src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))


@pytest.fixture
def skill_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    home = tmp_path / "home"
    target = home / ".agents"
    workspace = tmp_path / "workspace"
    (target / "skills").mkdir(parents=True)
    workspace.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home, target, workspace


def _write_skill(root: Path, skill_id: str = "write-report", *, enabled: bool = True) -> Path:
    path = root / skill_id / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {skill_id}\ndescription: Produce a concise report.\n"
        f"enabled: {str(enabled).lower()}\n---\n# Report\n\nWrite the approved report.\n",
        encoding="utf-8",
    )
    return path


def _freeze_skill(target: Path, artifacts: Path, skill_id: str, *, workspace_root: Path | None = None):
    shell = resolve_powershell()
    if shell is None:
        pytest.skip("PowerShell executable not available")
    organization = agent_direct_organization()
    organization["modules"][0].update({
        "candidate_skill_ids": [skill_id], "execution_mode": "skill_assigned",
    })
    organization["selected_skills"] = [{
        "skill_id": skill_id,
        "module_ids": ["direct_module"],
        "responsibility": "Write the approved report.",
        "reason": "The local Skill owns report delivery.",
    }]
    return run_freeze(
        shell, artifact_root=artifacts,
        env={**os.environ, "VCO_HOST_ID": "codex", "VIBE_AGENTS_HOME": str(target)},
        requested_stage_stop="xl_plan",
        host_decision={"agent_skill_organization": organization}, workspace_root=workspace_root,
    )


def _frozen_packet(artifacts: Path) -> dict[str, object]:
    return json.loads(next(artifacts.rglob("runtime-input-packet.json")).read_text(encoding="utf-8-sig"))


def test_canonical_freeze_rejects_a_skill_id_outside_declared_roots(skill_environment) -> None:
    home, target, workspace = skill_environment
    _write_skill(home)
    completed = _freeze_skill(target, workspace / "artifacts", "../../write-report")
    assert completed.returncode != 0, completed.stdout


@pytest.mark.parametrize("eligibility", ["enabled", "disabled", "missing_description"])
def test_canonical_admission_agrees_with_python_skill_eligibility(skill_environment, eligibility: str) -> None:
    from vgo_runtime.kernel.skill_index import build_skill_catalog

    home, target, workspace = skill_environment
    descriptor = _write_skill(target / "skills", enabled=eligibility != "disabled")
    if eligibility == "missing_description":
        descriptor.write_text("---\nname: write-report\n---\n# Report\n", encoding="utf-8")
    catalog = build_skill_catalog(agent_root=target, host_roots=(target / "skills",))
    eligible = any(row["active"] and row["enabled"] for row in catalog["entries"])
    assert eligible is (eligibility == "enabled")
    artifacts = workspace / "artifacts"
    completed = _freeze_skill(target, artifacts, "write-report")
    assert (completed.returncode == 0) is eligible, completed.stderr
    if eligible:
        unit = _frozen_packet(artifacts)["module_assignments"]["units"][0]
        assert unit["bound_skill"] == "write-report"
        assert Path(unit["skill_entrypoint"]) == descriptor.resolve()


@pytest.mark.parametrize("scope", ["user", "workspace"])
def test_canonical_admission_and_search_guide_honor_configured_skill_roots(skill_environment, scope: str) -> None:
    home, target, workspace = skill_environment
    root = workspace / "团队 skills"
    descriptor = _write_skill(root)
    config = (home if scope == "user" else workspace) / ".vibeskills/skill-roots.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(root)]}), encoding="utf-8")
    artifacts = workspace / "artifacts"
    completed = _freeze_skill(target, artifacts, "write-report", workspace_root=workspace)
    assert completed.returncode == 0, completed.stderr
    packet = _frozen_packet(artifacts)
    assert packet["module_assignments"]["units"][0]["skill_entrypoint"] == str(descriptor.resolve())
    assert {"kind": scope + "_extra", "path": str(root.resolve())} in packet["skill_search_guide"]["skill_roots"]


def test_cli_candidate_audit_uses_the_workspace_configured_skill_roots(skill_environment) -> None:
    import subprocess

    home, target, workspace = skill_environment
    root = workspace / "team skills"
    _write_skill(root)
    config = workspace / ".vibeskills/skill-roots.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(root)]}), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "vgo_cli.main", "route", "--repo-root", str(REPO_ROOT),
         "--target-root", str(target), "--host-id", "codex", "--workspace-root", str(workspace),
         "--prompt", "Produce a concise report.", "--requested-skill", "write-report", "--force-runtime-neutral"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["local_skill_index"]["host_roots"][0] == str(root.resolve())
    assert payload["candidate_focus"]["skill"] == "write-report"


def test_installed_runtime_hands_off_a_workspace_skill_and_replays_its_frozen_plan(skill_environment) -> None:
    for package in ("contracts", "installer-core"):
        source = REPO_ROOT / "packages" / package / "src"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from vgo_installer.simple_skill_installer import install_vibe_skill

    shell = resolve_powershell()
    if shell is None:
        pytest.skip("PowerShell executable not available")
    home, target, workspace = skill_environment
    descriptor = _write_skill(workspace / "团队 skills")
    config = workspace / ".vibeskills/skill-roots.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": 1, "extra_skill_roots": [str(descriptor.parent.parent)]}), encoding="utf-8")
    install_vibe_skill(repo_root=REPO_ROOT, skills_dir=target / "skills", installed_at_utc="2026-10-18T00:00:00Z")
    installed = target / "skills/vibe"
    artifacts = workspace / "artifacts"
    organization = agent_direct_organization()
    organization["modules"][0].update({"candidate_skill_ids": ["write-report"], "execution_mode": "skill_assigned"})
    organization["selected_skills"] = [{
        "skill_id": "write-report", "module_ids": ["direct_module"],
        "responsibility": "Write the approved report.", "reason": "The local Skill owns report delivery.",
    }]
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env.update({"VCO_HOST_ID": "codex", "VIBE_AGENTS_HOME": str(target), "PYTHONUTF8": "1"})
    completed = subprocess.run(
        [shell, "-NoProfile", "-File", str(installed / "scripts/runtime/invoke-vibe-runtime.ps1"),
         "-Task", "Write a concise report.", "-RunId", "installed-authority", "-RequestedStageStop", "plan_execute",
         "-HostDecisionJson", json.dumps({"agent_skill_organization": organization}),
         "-WorkspaceRoot", str(workspace), "-ArtifactRoot", str(artifacts)],
        cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(next(artifacts.rglob("runtime-summary.json")).read_text(encoding="utf-8-sig"))
    handoff = json.loads(Path(summary["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8-sig"))
    assert handoff["status"] == "agent_action_required"
    assert handoff["units"][0]["skill_entrypoint"] == str(descriptor.resolve())
    packet = next(artifacts.rglob("runtime-input-packet.json"))
    requirement = Path(summary["artifacts"]["requirement_doc"])
    replay = subprocess.run(
        [shell, "-NoProfile", "-File", str(installed / "scripts/runtime/Write-XlPlan.ps1"),
         "-Task", "Write a concise report.", "-RunId", "installed-authority",
         "-RuntimeInputPacketPath", str(packet), "-RequirementDocPath", str(requirement),
         "-ArtifactRoot", str(artifacts)],
        cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    assert replay.returncode == 0, replay.stderr
    plan = json.loads(next(artifacts.rglob("module-work-plan.json")).read_text(encoding="utf-8-sig"))
    assert plan["work_units"][0]["skill_id"] == "write-report"
