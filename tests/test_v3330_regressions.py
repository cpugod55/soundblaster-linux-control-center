import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "soundblaster_zse_control.py"

class V3330RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = APP.read_text()

    def test_version(self):
        self.assertIn('VERSION = "3.3.36"', self.text)

    def test_meter_prefers_physical_monitor(self):
        self.assertIn('candidate = f"{target}.monitor"', self.text)
        self.assertIn('candidate = f"{target}.monitor"', self.text)
        self.assertIn('["pw-record", "--raw", "--target=0"', self.text)
        self.assertIn('isolated PipeWire port meters', self.text)

    def test_meter_does_not_double_apply_channel_volume(self):
        worker = self.text[self.text.index('def analyzer_worker():'):self.text.index('def update_analyzer_canvas', self.text.index('def analyzer_worker():'))]
        self.assertNotIn('meter_levels_after_channel_controls(rms_display', worker)
        self.assertNotIn('["parec",', worker)

if __name__ == "__main__":
    unittest.main()
