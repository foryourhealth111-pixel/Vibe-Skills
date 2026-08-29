from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_root_readme_routes_lifecycle_commands_to_install_guide() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Some hosts may choose defaults such as" not in readme
    assert "./docs/install/README.en.md" in readme
    assert "install.ps1 -SkillsDir" not in readme
    assert "uninstall.ps1 -SkillsDir" not in readme
    assert "uninstall.ps1 -HostId <host>" not in readme
    assert "uninstall.sh --host <host>" not in readme


def test_root_chinese_readme_routes_lifecycle_commands_to_install_guide() -> None:
    readme = (REPO_ROOT / "README.zh.md").read_text(encoding="utf-8")

    assert "你也可以显式安装到 `~/.codex/skills` 或 `~/.claude/skills`" not in readme
    assert "有些宿主可以选择 `~/.agents/skills`、`~/.codex/skills` 或 `~/.claude/skills` 作为默认值" not in readme
    assert "./docs/install/README.md" in readme
    assert "install.ps1 -SkillsDir" not in readme
    assert "uninstall.ps1 -SkillsDir" not in readme
    assert "uninstall.ps1 -HostId <host>" not in readme
    assert "uninstall.sh --host <host>" not in readme


def test_install_guide_points_to_versioned_release_zip() -> None:
    guide = (REPO_ROOT / "docs" / "install" / "README.en.md").read_text(encoding="utf-8")

    assert "vibe-skills-4.1.0-public.zip" in guide
    assert "releases/download/v4.1.0/vibe-skills-4.1.0-public.zip" in guide
    assert "SHA-256 digest shown for the asset on the GitHub Release page" in guide
    assert "0b16a5f615a485b8d082407d458cc5c4ffe2cee443c6211fc941cd6678987dc9" not in guide


def test_install_readmes_describe_release_zip_not_repo_source_install() -> None:
    english = (REPO_ROOT / "docs" / "install" / "README.en.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "docs" / "install" / "README.md").read_text(encoding="utf-8")

    assert "published release zip" in english
    assert "repo's `vibe` skill" not in english
    assert "发布版本 zip" in chinese
    assert "仓库里的 `vibe` skill" not in chinese


def test_public_guidance_removes_vibe_by_deleting_the_folder() -> None:
    english = (REPO_ROOT / "docs" / "install" / "README.en.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "docs" / "install" / "README.md").read_text(encoding="utf-8")
    troubleshooting = (REPO_ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")

    assert "delete `<SkillsDir>/vibe`" in english
    assert "直接删除安装位置中的 `<SkillsDir>/vibe` 文件夹" in chinese
    assert "delete `<SkillsDir>/vibe`" in troubleshooting

    for content in (english, chinese, troubleshooting):
        assert "uninstall.ps1" not in content
        assert "uninstall.sh" not in content
        assert "-HostId" not in content
        assert "-Profile" not in content
        assert "-StrictOffline" not in content
        assert "-Deep" not in content
