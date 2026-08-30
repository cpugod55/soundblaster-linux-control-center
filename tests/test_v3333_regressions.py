import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()

class V3333RegressionTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.36"', APP)
    def test_crossover_uses_dark_disabled_style(self):
        self.assertIn('style.configure("SpeakerFill.TRadiobutton", background=CARD, foreground=TEXT)', APP)
        self.assertIn('background=[("disabled", CARD), ("active", CARD)]', APP)
        self.assertIn('foreground=[("disabled", MUTED), ("active", TEXT)]', APP)
        self.assertIn('style="SpeakerFill.TRadiobutton"', APP)

if __name__ == "__main__":
    unittest.main()
