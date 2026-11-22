import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app/soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()

class SpeakerLayout3357Tests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)

    def test_logical_layout_map_exists(self):
        self.assertIn('"2.1": ["FL", "FR", "LFE"]', APP)
        self.assertIn('"4.1": ["FL", "FR", "RL", "RR", "LFE"]', APP)
        self.assertIn('"5.0": ["FL", "FR", "RL", "RR", "FC"]', APP)

    def test_gui_uses_explicit_layout(self):
        self.assertIn('_REQUESTED_ACTIVE_POSITIONS = requested_layout_positions', APP)
        self.assertIn('ACTIVE_POSITIONS = _REQUESTED_ACTIVE_POSITIONS or sink_channel_positions', APP)

    def test_eq_generator_uses_explicit_layout(self):
        self.assertIn('_requested_positions = requested_layout_positions', APP)
        self.assertIn('positions=(_requested_positions or None)', APP)
        self.assertIn('dont_remix = "false" if target_is_51_transport and channel_count != 6 else "true"', APP)

    def test_digital_nonstereo_uses_ac3_carrier(self):
        self.assertGreaterEqual(INSTALL.count('"$CONNECTION" == "digital" && "$SPEAKER_LAYOUT" != "stereo"'), 2)
        self.assertIn('Digital $SPEAKER_LAYOUT was explicitly requested', INSTALL)

    def test_digital_stereo_reclaims_iec958(self):
        self.assertIn('Explicit Digital + stereo uses the normal IEC958 PCM profile', INSTALL)
        self.assertIn('rm -f "$A52_PULSE_CONF"', INSTALL)
        self.assertIn('output:iec958-stereo', INSTALL)

    def test_selection_persisted_before_graph_generation(self):
        pos = INSTALL.index("cur['speaker_layout']=sys.argv[3]")
        gen = INSTALL.index('--generate-eq-config')
        self.assertLess(pos, gen)

    def test_apply_relaunches_gui(self):
        self.assertIn('Output setup complete. Relaunching Sound Blaster Linux Control Center', APP)

    def test_fill_loopback_matches_logical_layout(self):
        self.assertIn('fill_positions = requested_layout_positions(settings.get("speaker_layout"))', APP)
        self.assertIn('audio.channels = {fill_channels} audio.position = [ {fill_position_text} ]', APP)

    def test_non51_speaker_test_uses_logical_order(self):
        self.assertIn('number = normalized.index(wanted) + 1', APP)

    def test_apply_closes_old_gui_before_relaunch(self):
        self.assertTrue('root.after(200, on_close)' in APP or 'os._exit(0)' in APP)

if __name__ == '__main__':
    unittest.main()
