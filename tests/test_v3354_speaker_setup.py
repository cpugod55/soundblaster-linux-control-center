import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app/soundblaster_zse_control.py').read_text()
INSTALL=(ROOT/'install.sh').read_text()

class V3354SpeakerSetupTests(unittest.TestCase):
    def test_new_state_defaults(self):
        self.assertIn('"output_connection": "auto"', APP)
        self.assertIn('"speaker_layout": "auto"', APP)
        self.assertIn('"fill_engine": "application"', APP)
    def test_presets_moved_to_main_page(self):
        self.assertIn('Save / Rename:', APP)
        self.assertNotIn('CUSTOM PRESET LIBRARY', APP)
        self.assertNotIn('★  Presets & Test', APP)
    def test_speaker_setup_controls(self):
        self.assertIn('▣  Speaker Setup', APP)
        self.assertIn('values=("auto","digital","analog")', APP)
        self.assertIn('MANUAL_LAYOUTS=("stereo","2.1","4.0","4.1","5.0","5.1")', APP)
        self.assertIn('values=("application","pipewire")', APP)
    def test_output_setup_reuses_distro_installer(self):
        self.assertIn('setup"/"install.sh"', APP)
        self.assertIn('--connection', APP)
        self.assertIn('--layout', APP)
        self.assertIn('SETUP_STAGE="$(mktemp -d)"', INSTALL)
    def test_fill_engine_selects_explicit_or_compat(self):
        self.assertIn('if engine == "pipewire":', APP)
        self.assertIn('if engine == "application":', APP)

if __name__ == '__main__': unittest.main()
