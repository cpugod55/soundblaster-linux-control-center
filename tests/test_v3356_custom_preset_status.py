from pathlib import Path
import unittest

APP = (Path(__file__).resolve().parents[1] / "app" / "soundblaster_zse_control.py").read_text()

class CustomPresetStatusTests(unittest.TestCase):
    def test_custom_recall_updates_bottom_status(self):
        self.assertIn('set_active_preset(f"custom:{slot}", display)', APP)
        self.assertIn('status_var.set(f"Preset loaded: {display}")', APP)

    def test_builtin_and_custom_use_same_status_wording(self):
        self.assertIn('status_var.set(f"Preset loaded: {name}")', APP)
        self.assertIn('status_var.set(f"Preset loaded: {display}")', APP)

    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

if __name__ == '__main__':
    unittest.main()
