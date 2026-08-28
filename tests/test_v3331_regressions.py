import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "soundblaster_zse_control.py"

class V3331RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = APP.read_text()

    def test_version(self):
        self.assertIn('VERSION = "3.3.35"', self.text)

    def test_meter_uses_explicit_pipewire_links(self):
        self.assertIn('["pw-record", "--raw", "--target=0"', self.text)
        self.assertIn('f"{hardware_sink}:monitor_{pos}"', self.text)
        self.assertIn('f"{node_name}:input_MONO"', self.text)
        self.assertIn('run(["pw-link", output_port, input_port]', self.text)

    def test_meter_does_not_use_pulse_capture(self):
        worker = self.text[self.text.index('def analyzer_worker():'):self.text.index('def update_analyzer_canvas', self.text.index('def analyzer_worker():'))]
        self.assertNotIn('["parec",', worker)
        self.assertNotIn('f"--target={source}"', worker)

    def test_meter_reports_capture_errors(self):
        self.assertIn('Analyzer error •', self.text)

if __name__ == "__main__":
    unittest.main()
