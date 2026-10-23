from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages/runtime-core/src"))

from vgo_runtime.kernel import codex_plugins, skill_index


@pytest.fixture
def host_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request):
    cache = tmp_path / "home" / getattr(request, "param", ".codex") / "plugins/cache"
    executable = cache.parent / ".plugin-appserver" / ("codex.exe" if os.name == "nt" else "codex")
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setenv("CODEX_HOME", str(cache.parent.parent))
    plugin = {"pluginId": "documents@provider", "name": "documents", "marketplaceName": "provider", "version": "2.0.0", "installed": True, "enabled": True}
    response = subprocess.CompletedProcess([], 0, stdout=json.dumps({"installed": [plugin]}), stderr="")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return response

    monkeypatch.setattr(codex_plugins.subprocess, "run", run)
    return cache, plugin, response, calls


def test_inventory_uses_exact_enabled_host_version(host_inventory) -> None:
    cache, plugin, response, calls = host_inventory
    disabled = {**plugin, "pluginId": "other@provider", "name": "other", "enabled": False}
    response.stdout = json.dumps({"installed": [plugin, disabled]})
    assert codex_plugins.resolve_codex_plugin_roots(cache) == ((cache / "provider/documents/2.0.0").resolve(),)
    command, kwargs = calls[0]
    assert command[1:] == ["plugin", "list", "--json"]
    assert kwargs["timeout"] == 5
    assert kwargs["env"]["CODEX_HOME"] == str(cache.parent.parent.resolve())


@pytest.mark.parametrize("field,value", [("version", "../outside"), ("name", "../outside"), ("marketplaceName", "D:"), ("pluginId", "other@provider"), ("enabled", "true"), ("installed", 1)])
def test_inventory_rejects_malformed_identity_and_flags(host_inventory, field, value) -> None:
    cache, plugin, response, _ = host_inventory
    plugin[field] = value
    response.stdout = json.dumps({"installed": [plugin]})
    with pytest.raises(ValueError, match="inventory"):
        codex_plugins.resolve_codex_plugin_roots(cache)


@pytest.mark.parametrize("payload", ["[]", "{}", "{", '{"installed":{}}'])
def test_inventory_rejects_malformed_payload(host_inventory, payload) -> None:
    cache, _, response, _ = host_inventory
    response.stdout = payload
    with pytest.raises(ValueError, match="inventory"):
        codex_plugins.resolve_codex_plugin_roots(cache)


def test_inventory_rejects_conflicting_enabled_versions(host_inventory) -> None:
    cache, plugin, response, _ = host_inventory
    response.stdout = json.dumps({"installed": [plugin, {**plugin, "version": "1.0.0"}]})
    with pytest.raises(ValueError, match="conflicting"):
        codex_plugins.resolve_codex_plugin_roots(cache)


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_inventory_failure_does_not_admit_cached_copies(host_inventory, monkeypatch, failure) -> None:
    cache, _, response, _ = host_inventory
    skill = cache / "provider/documents/1.0.0/skills/documents/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: Documents\ndescription: Render formal documents.\n---\n", encoding="utf-8")
    if failure == "exit":
        response.returncode = 1
    else:
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 5)
        monkeypatch.setattr(codex_plugins.subprocess, "run", timeout)
    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,))
    assert catalog["entries"] == []
    assert catalog["discovery_diagnostics"]["invalid_entries"][0]["reason"] == "host_plugin_inventory_unavailable"


def test_explicitly_empty_inventory_excludes_stale_cache(host_inventory) -> None:
    cache, _, response, _ = host_inventory
    response.stdout = '{"installed":[]}'
    assert codex_plugins.resolve_codex_plugin_roots(cache) == ()


def test_discovered_cache_cannot_supply_a_host_executable(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "untrusted/.codex/plugins/cache"
    executable = cache.parent / ".plugin-appserver" / ("codex.exe" if os.name == "nt" else "codex")
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "trusted-host"))
    def run(*args, **kwargs):
        raise AssertionError("A discovered cache must not execute its own program")
    monkeypatch.setattr(codex_plugins.subprocess, "run", run)
    assert codex_plugins.resolve_codex_plugin_roots(cache) is None


def test_unconfigured_cache_does_not_invoke_a_global_cli(tmp_path: Path, monkeypatch) -> None:
    codex_home = tmp_path / "host-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    def which(*args, **kwargs):
        raise AssertionError("An unconfigured cache has no host inventory integration")
    monkeypatch.setattr(codex_plugins.shutil, "which", which)
    assert codex_plugins.resolve_codex_plugin_roots(codex_home / "plugins/cache") is None


@pytest.mark.parametrize("version_present", [True, False])
def test_inventory_skips_unknown_versions_without_losing_known_skills(host_inventory, version_present) -> None:
    cache, plugin, response, _ = host_inventory
    unknown = {**plugin, "pluginId": "local@provider", "name": "local", "version": None}
    if not version_present:
        del unknown["version"]
    response.stdout = json.dumps({"installed": [unknown, plugin]})
    for name in ("documents", "local"):
        skill = cache / f"provider/{name}/2.0.0/skills/{name}/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"---\nname: {name}\ndescription: Render formal documents.\n---\n", encoding="utf-8")
    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,))
    assert [entry["skill_id"] for entry in catalog["entries"]] == ["documents"]
    assert catalog["discovery_diagnostics"]["invalid_entries"] == []


@pytest.mark.parametrize("field,value", [("name", "../outside"), ("marketplaceName", "D:"), ("pluginId", "other@provider")])
def test_nullable_version_preserves_identity_validation(host_inventory, field, value) -> None:
    cache, plugin, response, _ = host_inventory
    response.stdout = json.dumps({"installed": [{**plugin, "version": None, field: value}]})
    with pytest.raises(ValueError, match="inventory"):
        codex_plugins.resolve_codex_plugin_roots(cache)


def test_nullable_version_cannot_hide_conflicting_identity(host_inventory) -> None:
    cache, plugin, response, _ = host_inventory
    response.stdout = json.dumps({"installed": [{**plugin, "version": None}, plugin]})
    with pytest.raises(ValueError, match="conflicting"):
        codex_plugins.resolve_codex_plugin_roots(cache)


@pytest.mark.parametrize("host_inventory", ["custom-codex-state"], indirect=True)
def test_catalog_discovers_plugins_in_custom_codex_home(host_inventory) -> None:
    cache, _, _, _ = host_inventory
    skill = cache / "provider/documents/2.0.0/skills/documents/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: Documents\ndescription: Render formal documents.\n---\n", encoding="utf-8")

    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,), host_id="codex")

    assert [entry["skill_id"] for entry in catalog["entries"] if entry["active"] and entry["enabled"]] == ["documents"]
    assert catalog["discovery_diagnostics"]["invalid_entries"] == []


def _write_plugin_skill(root: Path, name: str) -> None:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: Render formal documents.\n---\n", encoding="utf-8")


@pytest.mark.parametrize("manifest_path,export", [
    (".codex-plugin/plugin.json", "skills"),
    (".codex-plugin/plugin.json", "published"),
    (".claude-plugin/plugin.json", "published"),
    ("plugin.json", "skills"),
])
def test_catalog_respects_plugin_skill_exports(host_inventory, manifest_path: str, export: str) -> None:
    cache, _, _, _ = host_inventory
    plugin = cache / "provider/documents/2.0.0"
    manifest = plugin / manifest_path
    manifest.parent.mkdir(parents=True)
    payload = {"name": "documents", "skills": f"./{export}/"}
    if manifest_path == "plugin.json":
        payload = {"name": "documents", "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"}
        overlay = plugin / ".codex-plugin/plugin.json"
        overlay.parent.mkdir()
        overlay.write_text(json.dumps({"skills": "./examples/"}), encoding="utf-8")
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    _write_plugin_skill(plugin / export, "documents")
    _write_plugin_skill(plugin / export / "documents/examples", "nested-example")
    _write_plugin_skill(plugin / "examples", "internal-example")

    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,), host_id="codex")

    assert [entry["skill_id"] for entry in catalog["entries"] if entry["active"] and entry["enabled"]] == ["documents"]
    assert catalog["discovery_diagnostics"]["invalid_entries"] == []


@pytest.mark.parametrize("manifest_text", [
    '{"skills":"./../outside"}', '{"skills":null}', '[]', '{',
    json.dumps({"skills": "./skills/.."}), json.dumps({"skills": "./skills\\.."}),
])
def test_invalid_plugin_exports_do_not_hide_other_plugins(host_inventory, manifest_text: str) -> None:
    cache, plugin, response, _ = host_inventory
    other = {**plugin, "pluginId": "notes@provider", "name": "notes"}
    response.stdout = json.dumps({"installed": [plugin, other]})
    for name in ("documents", "notes"):
        _write_plugin_skill(cache / f"provider/{name}/2.0.0/skills", name)
    manifest = cache / "provider/documents/2.0.0/.codex-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(manifest_text, encoding="utf-8")

    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,), host_id="codex")

    assert [entry["skill_id"] for entry in catalog["entries"]] == ["notes"]
    assert [row["reason"] for row in catalog["discovery_diagnostics"]["invalid_entries"]] == ["invalid_plugin_exports"]


def test_plugin_skill_exports_accept_skill_root_without_resource_skills(host_inventory) -> None:
    cache, _, _, _ = host_inventory
    plugin = cache / "provider/documents/2.0.0"
    _write_plugin_skill(plugin, "documents")
    _write_plugin_skill(plugin / "documents/examples", "nested-example")
    manifest = plugin / ".codex-plugin/plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"skills": "./documents/"}), encoding="utf-8")

    catalog = skill_index.scan_skill_catalog(agent_root=cache.parents[3] / "agent", host_roots=(cache,), host_id="codex")

    assert [entry["skill_id"] for entry in catalog["entries"] if entry["active"] and entry["enabled"]] == ["documents"]
    assert catalog["discovery_diagnostics"]["invalid_entries"] == []
