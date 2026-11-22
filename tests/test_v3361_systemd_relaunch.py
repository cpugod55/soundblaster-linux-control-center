import pathlib, unittest
ROOT = pathlib.Path(__file__).parents[1]
APP = (ROOT / 'app' / 'soundblaster_zse_control.py').read_text()
INSTALL = (ROOT / 'install.sh').read_text()
HELPER = (ROOT / 'app' / 'relaunch_helper.py').read_text()

class TestV3361SystemdRelaunch(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
    def test_gui_no_longer_owned_by_transient_unit(self):
        block = APP[APP.index('def apply_output_setup():'):APP.index('ttk.Label(setup_frame,text="Connection"')]
        self.assertNotIn('systemd-run --user --collect', block)
        self.assertNotIn('gtk-launch', block)
        self.assertIn('--request {old_gui_pid}', block)
    def test_persistent_service_survives_gui_exit(self):
        self.assertIn('Type=simple', INSTALL)
        self.assertIn('Restart=on-failure', INSTALL)
        self.assertIn('server.accept()', HELPER)
    def test_old_relaunch_path_removed(self):
        self.assertNotIn('nohup setsid', APP)
        self.assertNotIn('kill -0 "$oldpid"', APP)
