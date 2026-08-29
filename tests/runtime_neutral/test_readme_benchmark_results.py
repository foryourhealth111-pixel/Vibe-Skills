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
        for text in required_text:
            assert text in readme
        for asset_name in ASSET_DIMENSIONS:
            assert f"./docs/assets/{asset_name}" in readme
        assert "195" in readme
        assert "82" in readme
        assert "81" in readme
        assert "r33-lean-vibe-v4" in readme
        assert "src-3a61f181" in readme
        assert "bld-4c07b302" in readme
        assert "foryourhealth111-pixel/vibeskills-benchmark" in readme


def test_readme_benchmark_figures_are_local_high_resolution_pngs() -> None:
    for asset_name, dimensions in ASSET_DIMENSIONS.items():
        asset_path = ROOT / "docs" / "assets" / asset_name

        assert asset_path.is_file()
        assert _png_dimensions(asset_path) == dimensions
        assert asset_path.stat().st_size < 500_000
