#!/usr/bin/env python3
import argparse
import json
import shutil
import tempfile
from pathlib import Path

REQUIRED_CORE = [
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
]
REQUIRED_WORKFLOW = [
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
]
OPTIONAL_WORKFLOW = [
    "requesting-code-review",
    "receiving-code-review",
    "verification-before-completion",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def same_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def copy_dir_replace(src: Path, dst: Path):
    if not src.exists():
        return
    if same_path(src, dst):
        return

    src_resolved = src.resolve()
    dst_resolved = dst.resolve(strict=False)
    requires_staging = is_relative_to(src_resolved, dst_resolved) or is_relative_to(dst_resolved, src_resolved)

    if not requires_staging:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return

    stage_root = Path(tempfile.mkdtemp(prefix="vgo-copy-tree-"))
    try:
        staged = stage_root / src.name
        shutil.copytree(src, staged)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(staged, dst)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def copy_tree(src: Path, dst: Path):
    if not src.exists():
        return
    children = list(src.iterdir())
    dst.mkdir(parents=True, exist_ok=True)
    for child in children:
        target = dst / child.name
        if child.is_dir():
            copy_dir_replace(child, target)
        else:
            if target.exists() and same_path(child, target):
                continue
            shutil.copy2(child, target)


def copy_file(src: Path, dst: Path):
    if src.exists() and dst.exists() and same_path(src, dst):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def parent_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.resolve()
    parent = resolved.parent
    if parent == resolved or parent == Path(parent.anchor):
        return None
    return parent


def skill_source_roots(repo_root: Path) -> list[Path]:
    canonical_skills_root = parent_dir(repo_root)
    workspace_root = parent_dir(canonical_skills_root)
    candidates = [
        canonical_skills_root,
        workspace_root / "skills" if workspace_root is not None else None,
        workspace_root / "superpowers" / "skills" if workspace_root is not None else None,
        repo_root / "bundled" / "superpowers-skills",
    ]
    roots: list[Path] = []
    for candidate in candidates:
        if candidate is None or not candidate.exists():
            continue
        if candidate not in roots:
            roots.append(candidate)
    return roots


def embedded_registry():
    return {
        "schema_version": 1,
        "default_adapter_id": "codex",
        "aliases": {"claude": "claude-code"},
        "adapters": [
            {
                "id": "codex",
                "status": "supported-with-constraints",
                "install_mode": "governed",
                "check_mode": "governed",
                "bootstrap_mode": "governed",
                "default_target_root": {"env": "CODEX_HOME", "rel": ".vibeskills/targets/codex", "kind": "isolated-home"},
                "host_profile": "adapters/codex/host-profile.json",
                "settings_map": "adapters/codex/settings-map.json",
                "closure": "adapters/codex/closure.json",
                "manifest": "dist/host-codex/manifest.json",
            },
            {
                "id": "claude-code",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CLAUDE_HOME", "rel": ".vibeskills/targets/claude-code", "kind": "isolated-home"},
                "host_profile": "adapters/claude-code/host-profile.json",
                "settings_map": "adapters/claude-code/settings-map.json",
                "closure": "adapters/claude-code/closure.json",
                "manifest": "dist/host-claude-code/manifest.json",
            },
            {
                "id": "cursor",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "CURSOR_HOME", "rel": ".vibeskills/targets/cursor", "kind": "isolated-home"},
                "host_profile": "adapters/cursor/host-profile.json",
                "settings_map": "adapters/cursor/settings-map.json",
                "closure": "adapters/cursor/closure.json",
                "manifest": "dist/host-cursor/manifest.json",
            },
            {
                "id": "windsurf",
                "status": "preview",
                "install_mode": "runtime-core",
                "check_mode": "runtime-core",
                "bootstrap_mode": "runtime-core",
                "default_target_root": {"env": "WINDSURF_HOME", "rel": ".vibeskills/targets/windsurf", "kind": "isolated-home"},
                "host_profile": "adapters/windsurf/host-profile.json",
                "settings_map": "adapters/windsurf/settings-map.json",
                "closure": "adapters/windsurf/closure.json",
                "manifest": "dist/host-windsurf/manifest.json",
            },
            {
                "id": "openclaw",
                "status": "preview",
                "install_mode": "runtime-core",
                "check_mode": "runtime-core",
                "bootstrap_mode": "runtime-core",
                "default_target_root": {"env": "OPENCLAW_HOME", "rel": ".vibeskills/targets/openclaw", "kind": "isolated-home"},
                "host_profile": "adapters/openclaw/host-profile.json",
                "settings_map": "adapters/openclaw/settings-map.json",
                "closure": "adapters/openclaw/closure.json",
                "manifest": "dist/host-openclaw/manifest.json",
            },
            {
                "id": "opencode",
                "status": "preview",
                "install_mode": "preview-guidance",
                "check_mode": "preview-guidance",
                "bootstrap_mode": "preview-guidance",
                "default_target_root": {"env": "OPENCODE_HOME", "rel": ".vibeskills/targets/opencode", "kind": "isolated-home"},
                "host_profile": "adapters/opencode/host-profile.json",
                "settings_map": "adapters/opencode/settings-map.json",
                "closure": "adapters/opencode/closure.json",
                "manifest": "dist/host-opencode/manifest.json",
            },
        ],
    }


def resolve_registry(repo_root: Path):
    current = repo_root.resolve()
    while True:
        registry_path = current / "adapters" / "index.json"
        if registry_path.exists():
            return load_json(registry_path)
        if current.parent == current:
            break
        current = current.parent

    if (repo_root / "config" / "version-governance.json").exists():
        return embedded_registry()

    raise SystemExit(f"VGO adapter registry not found under repo root or ancestors: {repo_root}")


def resolve_adapter(repo_root: Path, host_id: str):
    registry = resolve_registry(repo_root)
    normalized = (host_id or registry.get("default_adapter_id") or "codex").strip().lower()
    normalized = registry.get("aliases", {}).get(normalized, normalized)
    for entry in registry.get("adapters", []):
        if entry.get("id") == normalized:
            return entry
    raise SystemExit(f"Unsupported VGO host id: {host_id}")


def sync_vibe_canonical(repo_root: Path, target_root: Path, target_rel: str):
    governance = load_json(repo_root / "config" / "version-governance.json")
    canonical_root = (repo_root / governance["source_of_truth"]["canonical_root"]).resolve()
    target_vibe_root = target_root / target_rel
    for rel in governance["packaging"]["mirror"]["files"]:
        src = canonical_root / rel
        if src.exists():
            copy_file(src, target_vibe_root / rel)
    for rel in governance["packaging"]["mirror"]["directories"]:
        src = canonical_root / rel
        dst = target_vibe_root / rel
        if src.exists():
            copy_dir_replace(src, dst)


def ensure_skill_present(target_root: Path, name: str, required: bool, allow_fallback: bool, fallback_sources, external_used, missing):
    skill_md = target_root / "skills" / name / "SKILL.md"
    if skill_md.exists():
        return
    if allow_fallback:
        for src in fallback_sources:
            src_path = Path(src)
            if src_path.exists():
                copy_tree(src_path, target_root / "skills" / name)
                external_used.add(name)
                break
    if required and not skill_md.exists():
        missing.add(name)


def install_runtime_core(repo_root: Path, target_root: Path, profile: str, allow_fallback: bool):
    packaging = load_json(repo_root / "config" / "runtime-core-packaging.json")
    for rel in packaging["directories"]:
        (target_root / rel).mkdir(parents=True, exist_ok=True)
    for entry in packaging["copy_directories"]:
        copy_tree(repo_root / entry["source"], target_root / entry["target"])
    for entry in packaging["copy_files"]:
        src = repo_root / entry["source"]
        if not src.exists():
            if entry.get("optional"):
                continue
            raise SystemExit(f"Runtime-core packaging source missing: {src}")
        copy_file(src, target_root / entry["target"])

    target_rel = packaging.get("canonical_vibe_mirror", {}).get("target_relpath", "skills/vibe")
    sync_vibe_canonical(repo_root, target_root, target_rel)

    roots = skill_source_roots(repo_root)

    external_used = set()
    missing = set()

    for name in REQUIRED_CORE:
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [
                root / name for root in roots
            ],
            external_used,
            missing,
        )
    for name in REQUIRED_WORKFLOW:
        ensure_skill_present(
            target_root,
            name,
            True,
            allow_fallback,
            [
                root / name for root in roots[1:] + roots[:1]
            ],
            external_used,
            missing,
        )
    if profile == "full":
        for name in OPTIONAL_WORKFLOW:
            ensure_skill_present(
                target_root,
                name,
                False,
                allow_fallback,
                [
                    root / name for root in roots[1:] + roots[:1]
                ],
                external_used,
                missing,
            )

    if missing:
        raise SystemExit("Missing required vendored skills: " + ", ".join(sorted(missing)))

    return sorted(external_used)


def install_codex_payload(repo_root: Path, target_root: Path):
    copy_tree(repo_root / "rules", target_root / "rules")
    copy_tree(repo_root / "agents" / "templates", target_root / "agents" / "templates")
    copy_tree(repo_root / "mcp", target_root / "mcp")
    (target_root / "config").mkdir(parents=True, exist_ok=True)
    copy_file(repo_root / "config" / "plugins-manifest.codex.json", target_root / "config" / "plugins-manifest.codex.json")
    settings_path = target_root / "settings.json"
    if not settings_path.exists():
        copy_file(repo_root / "config" / "settings.template.codex.json", settings_path)


def install_claude_guidance_payload(repo_root: Path, target_root: Path):
    # Hook and preview-settings installation are intentionally frozen until
    # cross-host compatibility issues are resolved.
    return


def install_opencode_guidance_payload(repo_root: Path, target_root: Path):
    commands_root = repo_root / "config" / "opencode" / "commands"
    agents_root = repo_root / "config" / "opencode" / "agents"
    example_config = repo_root / "config" / "opencode" / "opencode.json.example"

    copy_tree(commands_root, target_root / "commands")
    copy_tree(commands_root, target_root / "command")
    copy_tree(agents_root, target_root / "agents")
    copy_tree(agents_root, target_root / "agent")
    if example_config.exists():
        copy_file(example_config, target_root / "opencode.json.example")

def install_runtime_core_mode_payload(repo_root: Path, target_root: Path):
    commands_root = repo_root / "commands"
    if commands_root.exists():
        copy_tree(commands_root, target_root / "global_workflows")

    mcp_template = repo_root / "mcp" / "servers.template.json"
    mcp_config = target_root / "mcp_config.json"
    if mcp_template.exists() and not mcp_config.exists():
        copy_file(mcp_template, mcp_config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--profile", choices=("minimal", "full"), default="full")
    parser.add_argument("--allow-external-skill-fallback", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    target_root = Path(args.target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    adapter = resolve_adapter(repo_root, args.host)
    external_used = install_runtime_core(repo_root, target_root, args.profile, args.allow_external_skill_fallback)
    mode = adapter["install_mode"]
    if mode == "governed":
        install_codex_payload(repo_root, target_root)
    elif mode == "preview-guidance":
        if adapter["id"] == "opencode":
            install_opencode_guidance_payload(repo_root, target_root)
        elif adapter["id"] in {"claude-code", "cursor"}:
            install_claude_guidance_payload(repo_root, target_root)
        else:
            raise SystemExit(f"Unsupported preview-guidance adapter id: {adapter['id']}")
    elif mode == "runtime-core":
        install_runtime_core_mode_payload(repo_root, target_root)
    else:
        raise SystemExit(f"Unsupported adapter install mode: {mode}")

    write_json(
        {
            "host_id": adapter["id"],
            "install_mode": mode,
            "target_root": str(target_root),
            "external_fallback_used": external_used,
        }
    )


if __name__ == "__main__":
    main()
