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
