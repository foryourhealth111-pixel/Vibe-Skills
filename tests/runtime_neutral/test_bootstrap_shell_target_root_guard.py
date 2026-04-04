from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class BootstrapShellTargetRootGuardTests(unittest.TestCase):
    def test_bootstrap_sh_rejects_cursor_root_for_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / '.cursor'
            result = subprocess.run(
                [
                    'bash',
                    str(REPO_ROOT / 'scripts' / 'bootstrap' / 'one-shot-setup.sh'),
                    '--host', 'codex',
                    '--profile', 'minimal',
                    '--skip-external-install',
                    '--target-root', str(target_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('Cursor home', result.stderr)

    def test_bootstrap_sh_rejects_opencode_root_for_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / '.opencode'
            result = subprocess.run(
                [
                    'bash',
                    str(REPO_ROOT / 'scripts' / 'bootstrap' / 'one-shot-setup.sh'),
                    '--host', 'codex',
                    '--profile', 'minimal',
                    '--skip-external-install',
                    '--target-root', str(target_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn('OpenCode root', result.stderr)


if __name__ == '__main__':
    unittest.main()
