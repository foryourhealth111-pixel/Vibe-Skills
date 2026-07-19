from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"

CTA_CONTRACTS = {
    "en": {
        "readme": ROOT / "README.md",
        "label": "Install VibeSkills",
    },
    "cn": {
        "readme": ROOT / "README.zh.md",
        "label": "安装 VibeSkills",
    },
}


def _asset_names(language: str) -> tuple[str, str]:
    return (
        f"install-cta-{language}-light.svg",
        f"install-cta-{language}-dark.svg",
    )


def test_readmes_use_themed_install_cta_assets() -> None:
    for language, contract in CTA_CONTRACTS.items():
        readme = contract["readme"].read_text(encoding="utf-8")

        for asset_name in _asset_names(language):
            assert f"./docs/assets/{asset_name}" in readme
        assert f'alt="{contract["label"]}"' in readme
        assert f"./docs/assets/install-cta-{language}.svg" not in readme


def test_readmes_use_native_latest_release_links() -> None:
    labels = {
        "en": "Latest release · v4.0.0",
        "cn": "最新版本 · v4.0.0",
    }

    for language, contract in CTA_CONTRACTS.items():
        readme = contract["readme"].read_text(encoding="utf-8")

        assert labels[language] in readme
        assert "https://github.com/foryourhealth111-pixel/Vibe-Skills/releases/latest" in readme
        assert "img.shields.io/github/v/release" not in readme


def test_install_cta_assets_are_path_only_engraved_plaques() -> None:
    for language, contract in CTA_CONTRACTS.items():
        for asset_name in _asset_names(language):
            asset_path = ROOT / "docs" / "assets" / asset_name
            root = ET.parse(asset_path).getroot()
            tags = {element.tag for element in root.iter()}
            title = root.find(f"{SVG_NS}title")
            description = root.find(f"{SVG_NS}desc")
            download_icon = root.find(f".//*[@data-role='download-icon']")
            rectangles = root.findall(f"{SVG_NS}rect")

            assert root.tag == f"{SVG_NS}svg"
            assert root.attrib["viewBox"] == "0 0 300 54"
            assert f"{SVG_NS}text" not in tags
            assert f"{SVG_NS}style" not in tags
            assert len(root.findall(f".//{SVG_NS}path")) >= 4
            assert title is not None and title.text == contract["label"]
            assert description is not None and contract["label"] in (description.text or "")
            assert download_icon is not None
            assert rectangles
            assert max(float(rectangle.attrib.get("rx", "0")) for rectangle in rectangles) <= 4


def test_legacy_install_cta_assets_are_removed() -> None:
    assert not (ROOT / "docs" / "assets" / "install-cta-en.svg").exists()
    assert not (ROOT / "docs" / "assets" / "install-cta-cn.svg").exists()
