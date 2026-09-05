import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()


class V3336CompatibilityTests(unittest.TestCase):
    def test_profile_activation_is_capability_driven(self):
        self.assertIn('profile = "output:analog-surround-51"', APP)
        self.assertIn('pactl", "set-card-profile"', APP)
        self.assertIn('output:analog-surround-51', APP)

    def test_existing_surround_or_ac3_sink_is_not_replaced(self):
        helper = APP[APP.index('def activate_analog_surround51_profile'):APP.index('def normalize_channel_positions', APP.index('def activate_analog_surround51_profile'))]
        self.assertIn('if "surround-51" in target_sink or "ac3" in target_sink.lower():', helper)

    def test_profile_activation_happens_before_channel_detection(self):
        block = APP[APP.index('def ensure_configs'):APP.index('def restart_audio', APP.index('def ensure_configs'))]
        self.assertLess(block.index('target = activate_analog_surround51_profile(target)'), block.index('data["current"]["hardware_sink"] = target'))


if __name__ == "__main__":
    unittest.main()
