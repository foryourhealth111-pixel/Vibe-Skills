from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER_SRC = REPO_ROOT / "packages" / "installer-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
for src in (INSTALLER_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

import vgo_installer.install_runtime as install_runtime
from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface


def test_prune_previously_managed_wrapper_paths_removes_stale_wrapper_files(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    commands_root = target_root / "commands"
    commands_root.mkdir(parents=True, exist_ok=True)

    stale = commands_root / "vibe-how.md"
    current = commands_root / "vibe-how-do-we-do.md"
    stale.write_text("legacy\n", encoding="utf-8")
    current.write_text("current\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [
            str(stale),
            str(current),
        ]
    }

    install_runtime.prune_previously_managed_wrapper_paths(target_root, previous_ledger, [current])

    assert not stale.exists()
    assert current.exists()


def test_prune_previously_managed_wrapper_paths_ignores_outside_target_root(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir(parents=True, exist_ok=True)

    outside = tmp_path / "outside-vibe-how.md"
    outside.write_text("legacy\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [str(outside)]
    }

    install_runtime.prune_previously_managed_wrapper_paths(target_root, previous_ledger, [])

    assert outside.exists()


def test_prune_known_legacy_wrapper_paths_removes_untracked_codex_command_aliases(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    commands_root = target_root / "commands"
    commands_root.mkdir(parents=True, exist_ok=True)

    legacy = commands_root / "vibe-do.md"
    current = commands_root / "vibe-do-it.md"
    legacy.write_text("legacy\n", encoding="utf-8")
    current.write_text("current\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [
            str(legacy),
            str(current),
        ]
    }

    install_runtime.prune_known_legacy_wrapper_paths(target_root, "codex", [current], previous_ledger)

    assert not legacy.exists()
    assert current.exists()


def test_prune_known_legacy_wrapper_paths_removes_untracked_skill_aliases(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    legacy_root = target_root / "skills" / "vibe-how"
    current_root = target_root / "skills" / "vibe-how-do-we-do"
    legacy_root.mkdir(parents=True, exist_ok=True)
    current_root.mkdir(parents=True, exist_ok=True)
    (legacy_root / "SKILL.md").write_text("legacy\n", encoding="utf-8")
    current = current_root / "SKILL.md"
    current.write_text("current\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [
            str(legacy_root / "SKILL.md"),
            str(current),
        ]
    }

    install_runtime.prune_known_legacy_wrapper_paths(target_root, "claude-code", [current], previous_ledger)

    assert not legacy_root.exists()
    assert current.exists()


def test_prune_retired_discoverable_wrapper_paths_removes_nonpublic_wrapper_files_and_dirs(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    command_wrapper = target_root / "commands" / "vibe-how-do-we-do.md"
    skill_wrapper_root = target_root / "skills" / "vibe-do-it"
    command_wrapper.parent.mkdir(parents=True, exist_ok=True)
    skill_wrapper_root.mkdir(parents=True, exist_ok=True)
    command_wrapper.write_text("legacy discoverable wrapper\n", encoding="utf-8")
    (skill_wrapper_root / "SKILL.md").write_text("legacy discoverable skill wrapper\n", encoding="utf-8")

    entry_surface = load_discoverable_entry_surface(REPO_ROOT)
    current_wrapper = target_root / "commands" / "vibe.md"
    current_wrapper.write_text("current public wrapper\n", encoding="utf-8")
    previous_ledger = {
        "specialist_wrapper_paths": [
            str(command_wrapper),
            str(skill_wrapper_root / "SKILL.md"),
            str(current_wrapper),
        ]
    }

    install_runtime.prune_retired_discoverable_wrapper_paths(
        target_root,
        entry_surface,
        [current_wrapper],
        previous_ledger,
    )

    assert current_wrapper.exists()
    assert not command_wrapper.exists()
    assert not skill_wrapper_root.exists()


def test_prune_retired_discoverable_wrapper_paths_removes_previous_static_command_copies(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    command_wrapper = target_root / "commands" / "vibe-how-do-we-do.md"
    current_wrapper = target_root / "commands" / "vibe.md"
    command_wrapper.parent.mkdir(parents=True, exist_ok=True)
    command_wrapper.write_text("previous static copy\n", encoding="utf-8")
    current_wrapper.write_text("current public wrapper\n", encoding="utf-8")

    entry_surface = load_discoverable_entry_surface(REPO_ROOT)
    previous_ledger = {
        "created_paths": [
            str(command_wrapper),
            str(current_wrapper),
        ],
        "specialist_wrapper_paths": [
            str(current_wrapper),
        ],
    }

    install_runtime.prune_retired_discoverable_wrapper_paths(
        target_root,
        entry_surface,
        [current_wrapper],
        previous_ledger,
    )

    assert current_wrapper.exists()
    assert not command_wrapper.exists()


def test_copy_command_tree_with_public_vibe_entries_skips_nonpublic_vibe_commands(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "commands"
    dst_root = tmp_path / "target" / "commands"
    src_root.mkdir(parents=True)
    for name in (
        "non-vibe-helper.md",
        "vibe.md",
        "vibe-upgrade.md",
        "vibe-implement.md",
        "vibe-review.md",
        "vibe-what-do-i-want.md",
        "vibe-how-do-we-do.md",
        "vibe-do-it.md",
    ):
        (src_root / name).write_text(f"{name}\n", encoding="utf-8")

    entry_surface = load_discoverable_entry_surface(REPO_ROOT)

    install_runtime.copy_command_tree_with_public_vibe_entries(
        src_root,
        dst_root,
        entry_surface,
    )

    installed = {path.name for path in dst_root.iterdir()}
    assert {"non-vibe-helper.md", "vibe.md", "vibe-upgrade.md"}.issubset(installed)
    assert "vibe-implement.md" not in installed
    assert "vibe-review.md" not in installed
    assert "vibe-what-do-i-want.md" not in installed
    assert "vibe-how-do-we-do.md" not in installed
    assert "vibe-do-it.md" not in installed


def test_prune_known_legacy_wrapper_paths_preserves_same_name_user_owned_aliases(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    commands_root = target_root / "commands"
    commands_root.mkdir(parents=True, exist_ok=True)

    legacy = commands_root / "vibe-do.md"
    current = commands_root / "vibe-do-it.md"
    legacy.write_text("user-owned legacy alias\n", encoding="utf-8")
    current.write_text("current\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [
            str(current),
        ]
    }

    install_runtime.prune_known_legacy_wrapper_paths(target_root, "codex", [current], previous_ledger)

    assert legacy.exists()
    assert current.exists()


def test_prune_known_legacy_wrapper_paths_does_not_treat_broad_tracked_roots_as_wrapper_ownership(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    commands_root = target_root / "commands"
    commands_root.mkdir(parents=True, exist_ok=True)

    legacy = commands_root / "vibe-do.md"
    current = commands_root / "vibe.md"
    legacy.write_text("user-owned legacy alias\n", encoding="utf-8")
    current.write_text("current public wrapper\n", encoding="utf-8")

    previous_ledger = {
        "specialist_wrapper_paths": [str(current)],
        "created_paths": [str(target_root)],
        "owned_tree_roots": [str(commands_root)],
    }

    install_runtime.prune_known_legacy_wrapper_paths(target_root, "codex", [current], previous_ledger)

    assert legacy.exists()
    assert current.exists()


def test_prune_retired_discoverable_wrapper_paths_preserves_user_owned_same_name_wrappers(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    command_wrapper = target_root / "commands" / "vibe-how-do-we-do.md"
    skill_wrapper_root = target_root / "skills" / "vibe-do-it"
    current_wrapper = target_root / "commands" / "vibe.md"
    command_wrapper.parent.mkdir(parents=True, exist_ok=True)
    skill_wrapper_root.mkdir(parents=True, exist_ok=True)
    command_wrapper.write_text("user-owned wrapper\n", encoding="utf-8")
    (skill_wrapper_root / "SKILL.md").write_text("user-owned skill wrapper\n", encoding="utf-8")
    current_wrapper.write_text("current public wrapper\n", encoding="utf-8")

    entry_surface = load_discoverable_entry_surface(REPO_ROOT)
    previous_ledger = {
        "specialist_wrapper_paths": [
            str(current_wrapper),
        ]
    }

    install_runtime.prune_retired_discoverable_wrapper_paths(
        target_root,
        entry_surface,
        [current_wrapper],
        previous_ledger,
    )

    assert current_wrapper.exists()
    assert command_wrapper.exists()
    assert skill_wrapper_root.exists()
