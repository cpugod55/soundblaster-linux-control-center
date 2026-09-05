import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "app" / "soundblaster_zse_control.py"
INSTALL = Path(__file__).resolve().parents[1] / "install.sh"

class V3328RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SRC.read_text()
        cls.tree = ast.parse(cls.text)

    def test_version_and_installer_stamp(self):
        self.assertIn('VERSION = "3.3.38"', self.text)
        install = INSTALL.read_text()
        self.assertIn('VERSION="3.3.38"', install)
        self.assertIn("data['version']='3.3.38'", install)

    def test_live_meters_use_native_multichannel_capture(self):
        self.assertNotIn('def _start_semantic_meter_procs', self.text)
        self.assertIn('"--channels=1", "--channel-map=MONO"', self.text)

    def test_multichannel_capture_drives_discrete_meter_identity(self):
        self.assertIn('recorders[pos] = proc', self.text)
        self.assertIn('Combined spectrum from the same isolated physical outputs.', self.text)

    def test_generated_graph_prefers_saved_eq(self):
        self.assertIn('_saved_eq = _data.get("current", {}).get("eq", {})', self.text)
        self.assertIn('_gains = {f: float(_saved_eq.get(str(f)', self.text)

    def test_startup_eq_requires_stable_readback(self):
        self.assertIn('stable_matches = 0', self.text)
        self.assertIn('if stable_matches >= 2:', self.text)
        self.assertIn('restore_live_eq_verified(settings, attempts=10)', self.text)

if __name__ == '__main__':
    unittest.main()
