from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"

PREFACES = {
    "en": {
        "readme": ROOT / "README.md",
        "mobile_width": 360,
        "paragraphs": (
            "Skills are excellent local assets of reusable experience. After downloading and installing many Skills, it is easy to sometimes forget which Skills have already been installed and not know which Skills to invoke.",
            "Further, when a complex task involves the combined organization and invocation of multiple Skills from different domains, planning becomes complicated for people: they must explain to the AI in detail which Skills each module should use, while the AI may forget these designs during execution.",
            "Many current harness frameworks do not actively plan how to make good use of local Skill resources, and may even fall into an either-or scheduling conflict between the harness framework and domain Skill resources.",
            "The core of this project is to follow harness frameworks similar to Superpower and GSD. Based on modular decomposition by the planning state machine, it uses different Skills to assist different modules, fully schedules existing local resources, reduces users' planning and cognitive burden, and gives users an end-to-end delivery experience.",
            "It is committed to becoming a handy steward for the Skill resources around you. When a complex task appears, it can help users slowly sort out which modules are needed and which good experiences can be reused, then deliver an excellent result.",
        ),
    },
    "cn": {
        "readme": ROOT / "README.zh.md",
        "mobile_width": 320,
        "paragraphs": (
            "Skills是优秀的本地可复用经验资产。下载和安装了很多 skills 之后，很容易有些时候搞忘了已经安装了什么 skills，不知道该调用什么 skills。",
            "进一步，在复杂任务的时候,会涉及到不同领域的多个 skills 的复合组织调用时，人类规划起来比较复杂,要详细跟AI阐明每个模块要用什么skills，同时AI 在执行过程中可能会遗忘这些设计。",
            "而目前的 harness 框架很多并不会主动去规划好利用本地的skills资源，甚至有些时候陷入了harness框架和领域skills资源非此即彼的调度矛盾。",
            "这个项目的核心就是效仿 superpower 和 GSD 类似的 harness 框架，基于负责规划的状态机模块拆分，在每个不同的模块中使用不一样的 skills 来辅助任务，充分调度本地的已有资源，减少用户的规划和认知负担，给用户端到端的交付体验。",
            "致力于成为身边顺手的skills资源调度大管家，遇到复杂任务的时候，可以帮用户慢慢捋清楚要有哪些模块，有哪些好的经验可以复用，给用户最终交付一个优秀的结果。",
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
        assert 'width="900"' in readme
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
            assert len(root.findall(f".//*[@data-role='emphasis']")) >= 5
            assert len(root.findall(f".//*[@data-role='vision']")) >= 1
            assert description is not None
            assert all(
                paragraph in (description.text or "")
                for paragraph in contract["paragraphs"]
            )

            if "-mobile-" in asset_name:
                assert view_box[2] == contract["mobile_width"]
            else:
                assert view_box[2] == 960
