from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIEW_FILE = 'settings.vibe.preview.json'


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
        self.assertIsNone(payload['hooks_root'])
        self.assertIn('temporarily frozen', payload['message'])

    def test_powershell_scaffold_preserves_existing_settings_and_writes_preview_file(self) -> None:
        if shutil.which('pwsh') is None:
            self.skipTest('pwsh not available')
        cmd = [
            'pwsh',
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
        self.assertIsNone(payload['hooks_root'])
        self.assertIn('temporarily frozen', payload['message'])

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
        preview_path = self.target_root / PREVIEW_FILE
        self.assertEqual(self.existing_settings, json.loads(settings_path.read_text(encoding='utf-8')))
        self.assertFalse(preview_path.exists())
        self.assertEqual('preview-guidance', payload['install_mode'])

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

        self.assertIn('preview hook/settings scaffold remains intentionally unavailable', result.stdout)
        self.assertNotIn('[FAIL] settings.json', result.stdout)
        self.assertEqual(self.existing_settings, json.loads((self.target_root / 'settings.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
