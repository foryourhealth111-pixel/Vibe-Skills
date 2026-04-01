from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIEW_FILE = 'settings.vibe.preview.json'


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class ClaudePreviewScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.target_root = self.root / 'target'
        self.target_root.mkdir(parents=True, exist_ok=True)
        self.existing_settings = {
            'env': {
                'ANTHROPIC_BASE_URL': 'https://api.example.com/v1',
                'ANTHROPIC_AUTH_TOKEN': 'secret-token',
            },
            'model': 'existing-model',
        }
        (self.target_root / 'settings.json').write_text(
            json.dumps(self.existing_settings, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_shell_scaffold_preserves_existing_settings_and_writes_preview_file(self) -> None:
        cmd = [
            'bash',
            str(REPO_ROOT / 'scripts' / 'bootstrap' / 'scaffold-claude-preview.sh'),
            '--repo-root',
            str(REPO_ROOT),
            '--target-root',
            str(self.target_root),
            '--force',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)

        settings_path = self.target_root / 'settings.json'
        preview_path = self.target_root / PREVIEW_FILE
        self.assertEqual(self.existing_settings, json.loads(settings_path.read_text(encoding='utf-8')))
        self.assertFalse(preview_path.exists())
        self.assertIsNone(payload['preview_settings_path'])
        self.assertNotIn('hooks_root', payload)
        self.assertIn('no longer installs managed hooks', payload['message'])

    def test_powershell_scaffold_preserves_existing_settings_and_writes_preview_file(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest('PowerShell executable not available in PATH')
        cmd = [
            powershell,
            '-NoProfile',
            '-File',
            str(REPO_ROOT / 'scripts' / 'bootstrap' / 'scaffold-claude-preview.ps1'),
            '-RepoRoot',
            str(REPO_ROOT),
            '-TargetRoot',
            str(self.target_root),
            '-Force',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)

        settings_path = self.target_root / 'settings.json'
        preview_path = self.target_root / PREVIEW_FILE
        self.assertEqual(self.existing_settings, json.loads(settings_path.read_text(encoding='utf-8')))
        self.assertFalse(preview_path.exists())
        self.assertIsNone(payload['preview_settings_path'])
        self.assertNotIn('hooks_root', payload)
        self.assertIn('no longer installs managed hooks', payload['message'])

    def test_install_script_preserves_existing_settings_and_writes_preview_file(self) -> None:
        cmd = [
            'python3',
            str(REPO_ROOT / 'scripts' / 'install' / 'install_vgo_adapter.py'),
            '--repo-root',
            str(REPO_ROOT),
            '--target-root',
            str(self.target_root),
            '--host',
            'claude-code',
            '--profile',
            'full',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)

        settings_path = self.target_root / 'settings.json'
        closure_path = self.target_root / '.vibeskills' / 'host-closure.json'
        host_settings_path = self.target_root / '.vibeskills' / 'host-settings.json'
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        self.assertEqual(self.existing_settings['env'], settings['env'])
        self.assertEqual(self.existing_settings['model'], settings['model'])
        self.assertEqual('claude-code', settings['vibeskills']['host_id'])
        self.assertTrue(settings['vibeskills']['managed'])
        self.assertEqual(str((self.target_root / 'skills').resolve()), settings['vibeskills']['skills_root'])
        self.assertNotIn('hooks', settings)
        self.assertNotIn('managed_hook_command', settings['vibeskills'])
        self.assertTrue(closure_path.exists())
        self.assertTrue(host_settings_path.exists())
        self.assertFalse((self.target_root / 'hooks').exists())
        self.assertFalse((self.target_root / 'commands').exists())
        self.assertEqual('preview-guidance', payload['install_mode'])
        self.assertEqual(str(closure_path), payload['host_closure_path'])

    def test_preview_check_accepts_preview_settings_file_without_touching_real_settings(self) -> None:
        install_cmd = [
            'bash',
            str(REPO_ROOT / 'install.sh'),
            '--host',
            'claude-code',
            '--target-root',
            str(self.target_root),
            '--profile',
            'full',
        ]
        subprocess.run(install_cmd, capture_output=True, text=True, check=True)

        check_cmd = [
            'bash',
            str(REPO_ROOT / 'check.sh'),
            '--host',
            'claude-code',
            '--profile',
            'full',
            '--target-root',
            str(self.target_root),
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)

        self.assertIn('[OK] host closure manifest', result.stdout)
        self.assertIn('[OK] settings.json managed vibeskills node', result.stdout)
        settings = json.loads((self.target_root / 'settings.json').read_text(encoding='utf-8'))
        self.assertEqual(self.existing_settings['env'], settings['env'])
        self.assertEqual(self.existing_settings['model'], settings['model'])
        self.assertEqual('claude-code', settings['vibeskills']['host_id'])
        self.assertTrue((self.target_root / '.vibeskills' / 'host-settings.json').exists())
        self.assertFalse((self.target_root / 'hooks').exists())
        self.assertNotIn('hooks', settings)
        self.assertFalse((self.target_root / 'commands').exists())


if __name__ == '__main__':
    unittest.main()
