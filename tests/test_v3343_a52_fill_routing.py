from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app/soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()

class A52FillRoutingTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('VERSION="3.3.7"', INSTALL)
        self.assertIn("data['version']='3.3.7'", INSTALL)

    def test_a52_uses_dedicated_fill_route(self):
        self.assertIn('return current.get("hardware_sink", "") == "alsa_output.soundblaster_a52_51"', APP)
        self.assertIn('return current.get("hardware_sink", "") == "alsa_output.soundblaster_a52_51"', APP)
        self.assertIn('return uses_dedicated_fill_route(settings) or uses_explicit_fill_dsp(settings)', APP)

    def test_a52_fill_change_does_not_restart_pulse(self):
        self.assertIn('if not dedicated_fill and previous_text != new_text:', APP)
        self.assertIn('refreshed = restart_pipewire_pulse_defaults()', APP)

    def test_a52_route_is_maintained_off_gui_thread(self):
        self.assertIn('def fill_route_maintenance_worker():', APP)
        self.assertIn('route_speaker_fill_streams(current, force_restart=False, wait_for_lock=False)', APP)
        poll = APP[APP.index('def update_connection_status():'):APP.index('def analyzer_source_name():')]
        self.assertNotIn('route_speaker_fill_streams(', poll)

    def test_a52_fill_loopback_allows_remix(self):
        self.assertIn('stream.dont-remix = false', APP)
        self.assertNotIn('node.passive = true stream.dont-remix = true', APP)

    def test_installer_disables_global_upmix_for_a52(self):
        self.assertIn("target == 'alsa_output.soundblaster_a52_51'", INSTALL)
        self.assertIn("upmix='false' if compatibility or mode == 'OFF' else 'true'", INSTALL)

if __name__ == '__main__':
    unittest.main()
