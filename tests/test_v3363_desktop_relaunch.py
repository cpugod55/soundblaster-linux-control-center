from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()
HELPER = (ROOT / "app" / "relaunch_helper.py").read_text()

class TestPersistentRelaunch(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

    def test_output_setup_requests_persistent_helper(self):
        block = APP[APP.index('def apply_output_setup():'):APP.index('ttk.Label(setup_frame,text="Connection"')]
        self.assertIn('relaunch_helper.py', block)
        self.assertIn('--request {old_gui_pid}', block)
        self.assertNotIn('gtk-launch', block)
        self.assertNotIn('systemd-run --user --collect', block)

    def test_installer_creates_long_lived_user_service(self):
        self.assertIn('soundblaster-zse-relaunch-helper.service', INSTALL)
        self.assertIn('ExecStart=/usr/bin/python3 $LIB_DIR/relaunch_helper.py', INSTALL)
        self.assertIn('enable --now soundblaster-zse-relaunch-helper.service', INSTALL)

    def test_helper_launches_gui_directly(self):
        self.assertIn('[str(LAUNCHER)]', HELPER)
        self.assertIn('server.listen(4)', HELPER)
        self.assertIn('launch_after_exit', HELPER)

if __name__ == '__main__':
    unittest.main()
