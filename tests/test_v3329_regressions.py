import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "soundblaster_zse_control.py"
INSTALL = ROOT / "install.sh"

class V3329RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SRC.read_text()
        cls.tree = ast.parse(cls.text)

    def test_version_and_installer_stamp(self):
        self.assertIn('VERSION = "3.3.36"', self.text)
        install = INSTALL.read_text()
        self.assertIn('VERSION="3.3.36"', install)
        self.assertIn("data['version']='3.3.36'", install)

    def test_meter_backend_remains_discrete_and_native_ordered(self):
        self.assertNotIn('def _start_semantic_meter_procs', self.text)
        self.assertIn('"--channels=1", "--channel-map=MONO"', self.text)
        self.assertIn('recorders[pos] = proc', self.text)

    def test_startup_eq_fix_preserved(self):
        self.assertIn('restore_live_eq_verified(settings, attempts=10)', self.text)
        self.assertIn('if stable_matches >= 2:', self.text)

if __name__ == '__main__':
    unittest.main()
