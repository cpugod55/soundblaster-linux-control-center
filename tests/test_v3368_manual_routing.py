import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()

class ManualRoutingTests(unittest.TestCase):
    def test_manual_recovery_exists(self):
        self.assertIn("def select_soundblaster_explicitly(move_existing=True):", APP)
        self.assertIn('text="Use Sound Blaster"', APP)
        self.assertIn('"pactl", "set-default-sink", SINK', APP)

    def test_own_streams_excluded(self):
        self.assertIn('if stream["node"] in (OUTPUT_NODE, FILL_OUTPUT_NODE, FILL_LOOP_NAME):', APP)

    def test_background_respects_other_devices(self):
        self.assertIn('and soundblaster_default_selected():', APP)
        self.assertIn('now_sb and not previously_sb', APP)

    def test_analog_experimental_notice(self):
        self.assertIn('ANALOG_EXPERIMENTAL_LAYOUTS = frozenset(("4.0", "4.1", "5.0", "5.1"))', APP)
        self.assertIn('EXPERIMENTAL — Analog speaker configurations above 2.1', APP)
