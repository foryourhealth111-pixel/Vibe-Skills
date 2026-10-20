import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIMENSIONS = {
    "skillsbench-task-outcomes.png": (2961, 998),
    "skillsbench-resource-use.png": (3186, 1059),
}


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">II", payload[16:24])


def test_readmes_show_benchmark_results_before_the_long_preface() -> None:
    summary = json.loads((ROOT / "config/benchmark-results.json").read_text(encoding="utf-8"))
    contracts = {
        "README.md": (
            "Measured on SkillsBench",
            "Mean verifier reward: +21.12 pp",
            "Total tokens: -29.6%",
            "Tool calls: -33.1%",
        ),
        "README.zh.md": (
            "SkillsBench 实测表现",
            "平均 Verifier Reward：+21.12 个百分点",
            "总 Token：-29.6%",
            "工具调用：-33.1%",
        ),
    }

    for readme_name, required_text in contracts.items():
        readme = (ROOT / readme_name).read_text(encoding="utf-8")
        section_start = readme.index('<a id="skillsbench-performance"></a>')
        preface_start = readme.index("readme-preface-v2-")

        assert section_start < preface_start
        benchmark_section = readme[section_start:preface_start]
        for text in required_text:
            assert text in benchmark_section
        for asset_name in ASSET_DIMENSIONS:
            assert f"./docs/assets/{asset_name}" in benchmark_section
        assert str(summary["benchmark"]["global_skill_names"]) in benchmark_section
        assert str(summary["analysis"]["paired_reward_tasks"]) in benchmark_section
        assert str(summary["analysis"]["paired_resource_tasks"]) in benchmark_section
        assert summary["study_id"] in benchmark_section
        assert summary["publication"]["commit"][:12] in benchmark_section
        assert './config/benchmark-results.json' in benchmark_section
        assert summary["publication"]["repository"] in benchmark_section


def test_readme_benchmark_figures_are_local_high_resolution_pngs() -> None:
    for asset_name, dimensions in ASSET_DIMENSIONS.items():
        asset_path = ROOT / "docs" / "assets" / asset_name

        assert asset_path.is_file()
        assert _png_dimensions(asset_path) == dimensions
        assert asset_path.stat().st_size < 500_000


def test_benchmark_summary_records_public_units_sample_sizes_and_provenance() -> None:
    import re

    summary = json.loads((ROOT / "config/benchmark-results.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert re.fullmatch(r"[0-9a-f]{40}", summary["publication"]["commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", summary["benchmark"]["source_commit"])
    assert re.fullmatch(r"[0-9a-f]{64}", summary["benchmark"]["global_skill_tree_sha256"])
    assert summary["analysis"]["paired_resource_tasks"] <= summary["analysis"]["paired_reward_tasks"]
    metrics = summary["headline_results"]
    delta = metrics["lean_vibe_mean_reward"] - metrics["native_mean_reward"]
    assert abs(delta - metrics["mean_reward_difference"]) < 1e-12
    assert abs(1 - metrics["lean_vibe_total_tokens"] / metrics["native_total_tokens"] - metrics["token_reduction"]) < 1e-12
    assert abs(1 - metrics["lean_vibe_tool_calls"] / metrics["native_tool_calls"] - metrics["tool_call_reduction"]) < 1e-12
    points = f'{metrics["mean_reward_difference"] * 100:.2f}'
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh.md").read_text(encoding="utf-8")
    assert f"{points} percentage points" in english
    assert f"{points} 个百分点" in chinese
    assert f"average task score by {points}%" not in english
    assert f"平均任务得分提升{points}%" not in chinese
