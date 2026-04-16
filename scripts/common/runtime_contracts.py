#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.installed_runtime_contract import (
    COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT,
    DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE,
    DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE,
    DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE,
    DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE,
    DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION,
    DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH,
    DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT,
    DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR,
    DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH,
    FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT,
    default_coherence_runtime_config,
    default_freshness_runtime_config,
    default_installed_runtime_config,
    merge_installed_runtime_config,
)
from vgo_contracts.canonical_vibe_contract import (
    DEFAULT_CANONICAL_VIBE_ENTRY_MODE,
    DEFAULT_CANONICAL_VIBE_FALLBACK_POLICY,
    DEFAULT_CANONICAL_VIBE_LAUNCHER_KIND,
    resolve_canonical_vibe_contract,
    uses_skill_only_activation,
)
from vgo_contracts.runtime_surface_contract import (
    DEFAULT_IGNORE_JSON_KEYS,
    DEFAULT_PACKAGING_DIRECTORIES,
    DEFAULT_PACKAGING_FILES,
    RUNTIME_IGNORED_DIR_NAMES,
    RUNTIME_IGNORED_FILE_NAMES,
    RUNTIME_IGNORED_FILE_PREFIXES,
    RUNTIME_IGNORED_SUFFIXES,
    is_ignored_runtime_artifact,
    load_json_file,
    resolve_packaging_contract,
)

__all__ = [
    "DEFAULT_CANONICAL_VIBE_ENTRY_MODE",
    "DEFAULT_CANONICAL_VIBE_FALLBACK_POLICY",
    "DEFAULT_CANONICAL_VIBE_LAUNCHER_KIND",
    "COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT",
    "DEFAULT_IGNORE_JSON_KEYS",
    "DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE",
    "DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE",
    "DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE",
    "DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE",
    "DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION",
    "DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH",
    "DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT",
    "DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR",
    "DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH",
    "DEFAULT_PACKAGING_DIRECTORIES",
    "DEFAULT_PACKAGING_FILES",
    "FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT",
    "RUNTIME_IGNORED_DIR_NAMES",
    "RUNTIME_IGNORED_FILE_NAMES",
    "RUNTIME_IGNORED_FILE_PREFIXES",
    "RUNTIME_IGNORED_SUFFIXES",
    "default_coherence_runtime_config",
    "default_freshness_runtime_config",
    "default_installed_runtime_config",
    "is_ignored_runtime_artifact",
    "load_json_file",
    "merge_installed_runtime_config",
    "resolve_canonical_vibe_contract",
    "resolve_packaging_contract",
    "uses_skill_only_activation",
]


def _emit_installed_runtime_config(mode: str) -> int:
    loaders = {
        "installed": default_installed_runtime_config,
        "freshness": default_freshness_runtime_config,
        "coherence": default_coherence_runtime_config,
    }
    payload = loaders[mode]()
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runtime contract bridge helpers")
    subparsers = parser.add_subparsers(dest="command")

    config_parser = subparsers.add_parser(
        "installed-runtime-config",
        help="Emit installed-runtime contract defaults as JSON for wrapper consumers.",
    )
    config_parser.add_argument(
        "--mode",
        choices=("installed", "freshness", "coherence"),
        default="installed",
    )

    args = parser.parse_args(argv)
    if args.command == "installed-runtime-config":
        return _emit_installed_runtime_config(args.mode)
    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
