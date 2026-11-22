from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()

class AboutPrivacyTests(unittest.TestCase):
    def test_version_stamps(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)

    def test_private_email_not_in_app(self):
        self.assertNotIn("zuestgg@gmail.com", APP)

    def test_project_links_present(self):
        self.assertIn("https://github.com/cpugod55/soundblaster-linux-control-center", APP)
        self.assertIn("https://github.com/cpugod55/soundblaster-linux-control-center/issues", APP)
        self.assertIn("https://github.com/sponsors/cpugod55", APP)

    def test_cinnamon_startup_notify_fix_preserved(self):
        self.assertIn("StartupNotify=false", INSTALL)

if __name__ == "__main__":
    unittest.main()
