import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()

class SpeakerSetup3359Tests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)

    def test_manual_layout_list_has_no_auto(self):
        self.assertIn('MANUAL_LAYOUTS=("stereo","2.1","4.0","4.1","5.0","5.1")', APP)
        self.assertNotIn('values=("auto","stereo","2.1","4.0","4.1","5.0","5.1")', APP)

    def test_auto_connection_disables_layout(self):
        self.assertIn('layout_combo.configure(state="disabled" if is_auto else "readonly")', APP)
        self.assertIn('speaker_layout_var.set("auto")', APP)

    def test_manual_connection_restores_detected_layout(self):
        self.assertIn('if speaker_layout_var.get() not in MANUAL_LAYOUTS:', APP)
        self.assertIn('speaker_layout_var.set(ACTIVE_LAYOUT if ACTIVE_LAYOUT in MANUAL_LAYOUTS else "5.1")', APP)

    def test_relaunch_uses_persistent_helper(self):
        block = APP[APP.index('def apply_output_setup():'):APP.index('ttk.Label(setup_frame,text="Connection"')]
        self.assertIn('relaunch_helper.py', block)
        self.assertIn('--request {old_gui_pid}', block)
        self.assertNotIn('nohup setsid', block)

if __name__ == '__main__':
    unittest.main()
