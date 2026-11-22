import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / 'app' / 'soundblaster_zse_control.py').read_text()
HELPER = (ROOT / 'app' / 'relaunch_helper.py').read_text()

class OutputSetupGuardTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

    def test_apply_guard_and_progress(self):
        self.assertIn('output_setup_in_progress', APP)
        self.assertIn('Applying output setup… Please wait. The app will restart automatically.', APP)
        self.assertIn('apply_output_button.state(["disabled"])', APP)

    def test_relaunch_settle_marker(self):
        self.assertIn('COOLDOWN_PATH.write_text', HELPER)
        self.assertIn('_apply_output_startup_guard()', APP)
        self.assertIn('Output setup complete — audio is settling. Please wait…', APP)
        self.assertIn('guard_seconds=4.0', APP)

if __name__ == '__main__':
    unittest.main()
