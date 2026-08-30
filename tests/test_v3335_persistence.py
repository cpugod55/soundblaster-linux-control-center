import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / 'app' / 'soundblaster_zse_control.py').read_text()
INSTALL = (ROOT / 'install.sh').read_text()
UPGRADE = (ROOT / 'UPGRADE_NOTES.md').read_text()
TROUBLE = (ROOT / 'TROUBLESHOOTING.md').read_text()

class PersistenceHardeningTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.36"', APP)
        self.assertIn('VERSION="3.3.36"', INSTALL)

    def test_app_state_write_is_atomic_and_keeps_previous(self):
        self.assertIn('STATE_FILE.name + ".tmp"', APP)
        self.assertIn('STATE_FILE.name + ".backup-last"', APP)
        self.assertIn('shutil.copy2(STATE_FILE, backup)', APP)
        self.assertIn('tmp.replace(STATE_FILE)', APP)

    def test_installer_backs_up_state_before_legacy_migration(self):
        backup = INSTALL.index('backup_if_exists "$STATE_DIR/state.json"')
        migration = INSTALL.index('if [[ ! -f "$STATE_DIR/state.json" && -f "$OLD_STATE" ]]')
        self.assertLess(backup, migration)

    def test_installer_refuses_root(self):
        self.assertIn('Do not run this installer with sudo/root', INSTALL)

    def test_jamesdsp_is_documented_not_dependency(self):
        self.assertIn('JamesDSP is not required', UPGRADE)
        self.assertIn('jamesdsp_sink', TROUBLE)

    def test_python_syntax(self):
        ast.parse(APP)

if __name__ == '__main__':
    unittest.main()
