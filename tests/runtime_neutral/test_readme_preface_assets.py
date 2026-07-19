from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"

PREFACES = {
    "en": {
        "readme": ROOT / "README.md",
        "paragraphs": (
            "Skills are valuable working assets. But as a task becomes more complex, an agent often falls back on the few Skills that are easiest to trigger, while the rest rarely enter the plan. When several Skills take part, responsibilities and outputs can also fail to connect.",
            "VibeSkills organizes these resources through a structured, host-neutral harness. It can be used in any AI application that supports local Skills.",
            "It draws on the harness approaches of Superpowers and GSD-Lite, with a complete workflow and state machine that bring requirement confirmation, execution planning, Skill organization, harness-guided execution, testing, and evaluation together.",
            "The goal is to give users an end-to-end delivery experience for concrete tasks while lowering the cognitive burden and barrier to using AI.",
            "Users should not have to worry that less frequently used Skills will sit idle, or repeatedly remember which Skills should be used for which task.",
        ),
    },
    "cn": {
        "readme": ROOT / "README.zh.md",
        "paragraphs": (
            "Skills 是优秀的实践资产，但是任务一复杂，Agent 往往反复调用最容易触发的几个，其余 Skills 很少被安排进计划；多个 Skills 一起参与时，分工和结果也容易接不上。",
            "VibeSkills 会通过一套规范化、宿主中立的 harness 把这些资源组织起来，可用于所有支持本地 Skills 的 AI 应用。",
            "它参考了 Superpowers 和 GSD-Lite 的 harness 方式，拥有完整的 harness 流程和状态机，把需求确认、执行规划、Skills 组织、框架化 harness 执行、测试与评估连接为一个整体。",
            "最终想要给用户完成具体任务的端到端交付体验，降低 AI 使用时的认知负担和门槛。",
            "让用户不再担心下载不常用的 Skills 而闲置，也不再担心不知道该用哪些 Skills 而需要反复记忆。",
        ),
    },
}


def _asset_names(language: str) -> tuple[str, ...]:
    return (
        f"readme-preface-{language}-light.svg",
        f"readme-preface-{language}-dark.svg",
        f"readme-preface-{language}-mobile-light.svg",
        f"readme-preface-{language}-mobile-dark.svg",
    )


def test_readmes_use_responsive_unnumbered_preface_assets() -> None:
    for language, contract in PREFACES.items():
        readme = contract["readme"].read_text(encoding="utf-8")

        for asset_name in _asset_names(language):
            assert f"./docs/assets/{asset_name}" in readme
        for paragraph in contract["paragraphs"]:
            assert paragraph in readme

        assert readme.count("(max-width: 600px)") >= 2
        assert "readme-preface" in readme
        assert "Ⅰ" not in readme
        assert "Ⅱ" not in readme
        assert "Ⅲ" not in readme


def test_preface_assets_are_path_only_and_accessible() -> None:
    for language, contract in PREFACES.items():
        for asset_name in _asset_names(language):
            asset_path = ROOT / "docs" / "assets" / asset_name
            root = ET.parse(asset_path).getroot()
            view_box = tuple(float(value) for value in root.attrib["viewBox"].split())
            tags = {element.tag for element in root.iter()}
            description = root.find(f"{SVG_NS}desc")

            assert root.tag == f"{SVG_NS}svg"
            assert f"{SVG_NS}text" not in tags
            assert f"{SVG_NS}style" not in tags
            assert len(root.findall(f".//{SVG_NS}path")) >= 6
            assert len(root.findall(f".//{SVG_NS}use")) >= 20
            assert description is not None
            assert all(
                paragraph in (description.text or "")
                for paragraph in contract["paragraphs"]
            )

            if "-mobile-" in asset_name:
                assert view_box[2] == 360
            else:
                assert view_box[2] == 960
