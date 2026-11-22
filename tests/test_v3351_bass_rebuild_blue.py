import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()

class V3351BassRebuildBlue(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)

    def test_dedicated_bass_rebuild_is_creation_time(self):
        self.assertIn('def rebuild_bass_management_graph(settings):', APP)
        self.assertIn('persist_bass_management_config(settings)', APP)
        self.assertIn('restart_filter_chain_service()', APP)
        self.assertIn('elif uses_dedicated_fill_route(DATA["current"]):', APP)
        self.assertIn('schedule_bass_management_rebuild()', APP)

    def test_rebuild_restores_verified_fill_and_calibration(self):
        self.assertIn('restore_live_eq_verified(settings, attempts=8)', APP)
        self.assertIn('apply_preamp(settings, bypass_var.get())', APP)
        self.assertIn('apply_channel_levels(settings, bypass_var.get())', APP)
        self.assertIn('route_speaker_fill_streams(settings, force_restart=False)', APP)

    def test_blue_accent_and_no_red_primary_accent(self):
        self.assertIn('ACCENT = "#1597d4"', APP)
        self.assertIn('ACCENT2 = "#45b8ee"', APP)
        self.assertNotIn('ACCENT = "#e53935"', APP)

    def test_v3350_explicit_fill_preserved(self):
        self.assertIn('def fill_dsp_config_text(settings):', APP)
        self.assertIn('def set_fill_filter_controls(settings):', APP)
        self.assertIn('uses_explicit_fill_dsp(settings)', APP)

if __name__ == "__main__":
    unittest.main()
