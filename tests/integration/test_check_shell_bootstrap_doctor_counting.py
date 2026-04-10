from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class CheckShellBootstrapDoctorCountingTests(unittest.TestCase):
    def test_bootstrap_doctor_plain_fail_branch_only_increments_fail(self) -> None:
        content = (REPO_ROOT / "check.sh").read_text(encoding="utf-8")
        self.assertIn(
            '    else\n'
            '      echo "[FAIL] vibe bootstrap doctor gate"\n'
            '      FAIL=$((FAIL+1))\n'
            '    fi',
            content,
        )
        self.assertNotIn(
            '    else\n'
            '      echo "[FAIL] vibe bootstrap doctor gate"\n'
            '      WARN=$((WARN+1))\n'
            '      FAIL=$((FAIL+1))\n'
            '    fi',
            content,
        )


if __name__ == "__main__":
    unittest.main()
