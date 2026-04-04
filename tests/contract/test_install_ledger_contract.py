from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages' / 'contracts' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vgo_contracts.install_ledger import InstallLedger


def test_install_ledger_rejects_invalid_skill_names() -> None:
    try:
        InstallLedger(managed_skill_names=['../bad'])
    except ValueError:
        assert True
    else:
        raise AssertionError('expected validation failure')
