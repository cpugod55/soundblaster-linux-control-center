import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "soundblaster_zse_control.py"

class V3332RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = APP.read_text()

    def test_version(self):
        self.assertIn('VERSION = "3.3.38"', self.text)

    def test_live_meters_use_isolated_mono_recorders(self):
        self.assertIn('"--channels=1", "--channel-map=MONO"', self.text)
        self.assertIn('f"{hardware_sink}:monitor_{pos}"', self.text)
        self.assertIn('f"{node_name}:input_MONO"', self.text)
        self.assertIn('recorders[pos] = proc', self.text)

    def test_shared_six_channel_recorder_removed_from_worker(self):
        worker = self.text[self.text.index('def analyzer_worker():'):self.text.index('def update_analyzer_canvas', self.text.index('def analyzer_worker():'))]
        self.assertNotIn('f"--channels={channels}"', worker)
        self.assertNotIn('f"--channel-map={pw_channel_map}"', worker)
        self.assertNotIn('vals[ch::channels]', worker)

    def test_spectrum_uses_same_isolated_outputs(self):
        self.assertIn('Combined spectrum from the same isolated physical outputs.', self.text)

if __name__ == "__main__":
    unittest.main()
