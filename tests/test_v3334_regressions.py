import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()


class V3334RegressionTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.36"', APP)

    def test_bazzite_channel_levels_select_physical_sink(self):
        helper = APP[APP.index('def channel_level_sink'):APP.index('def read_channel_levels', APP.index('def channel_level_sink'))]
        self.assertIn('if is_bazzite():', helper)
        self.assertIn('target = current.get("hardware_sink", "")', helper)
        self.assertIn('if target and sink_exists(target):', helper)
        self.assertIn('return target', helper)
        self.assertTrue(helper.rstrip().endswith('return SINK'))

    def test_apply_and_restore_use_selected_channel_level_sink(self):
        apply_block = APP[APP.index('def apply_channel_levels'):APP.index('def restore_log', APP.index('def apply_channel_levels'))]
        restore_block = APP[APP.index('def restore_channel_levels_verified'):APP.index('def combined_eq_peak_db', APP.index('def restore_channel_levels_verified'))]
        self.assertIn('target = channel_level_sink(settings)', apply_block)
        self.assertIn('["pactl", "set-sink-volume", target]', apply_block)
        self.assertNotIn('["pactl", "set-sink-volume", SINK]', apply_block)
        self.assertIn('target = channel_level_sink(settings)', restore_block)
        self.assertIn('actual = read_channel_levels(target)', restore_block)
        self.assertIn('stable = read_channel_levels(target)', restore_block)

    def test_ubuntu_fallback_remains_virtual_eq_sink(self):
        helper = APP[APP.index('def channel_level_sink'):APP.index('def read_channel_levels', APP.index('def channel_level_sink'))]
        self.assertTrue(helper.rstrip().endswith('return SINK'))


if __name__ == "__main__":
    unittest.main()
