import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
HELPER = (ROOT / "app" / "relaunch_helper.py").read_text()

class TestV3362UniqueRelaunch(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

    def test_transient_unit_relaunch_removed(self):
        block = APP[APP.index('def apply_output_setup():'):APP.index('ttk.Label(setup_frame,text="Connection"')]
        self.assertNotIn('relaunch_token=', block)
        self.assertNotIn('relaunch_unit=', block)
        self.assertNotIn('systemd-run --user', block)

    def test_persistent_helper_replaces_service_owned_gui(self):
        self.assertIn('SOCKET_PATH = RUNTIME_DIR / f"{APP_ID}-relaunch-helper.sock"', HELPER)
        self.assertIn('subprocess.Popen(', HELPER)
        self.assertIn('[str(LAUNCHER)]', HELPER)
        self.assertNotIn('gtk-launch', APP[APP.index('def apply_output_setup():'):])

if __name__ == '__main__':
    unittest.main()
