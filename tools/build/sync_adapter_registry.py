from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_CONFIG_RELATIVE_PATH = Path("config/adapter-registry.json")
OUTPUT_RELATIVE_PATH = Path("adapters/index.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_adapter_registry(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    return load_json(root / SOURCE_CONFIG_RELATIVE_PATH)


def sync_adapter_registry(repo_root: Path | str, *, output_root: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    target_root = root if output_root is None else Path(output_root).resolve()
    payload = build_adapter_registry(root)
    write_json(target_root / OUTPUT_RELATIVE_PATH, payload)
    return {
        "schema_version": 1,
        "generated": True,
        "repo_root": str(root),
        "output_root": str(target_root),
        "source_config": str((root / SOURCE_CONFIG_RELATIVE_PATH).resolve()),
        "generated_output": str(OUTPUT_RELATIVE_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate adapters/index.json from the authoritative adapter registry source.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default="")
    args = parser.parse_args()

    output_root = args.output_root or None
    result = sync_adapter_registry(args.repo_root, output_root=output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
