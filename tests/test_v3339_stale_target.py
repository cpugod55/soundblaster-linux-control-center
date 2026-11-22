import importlib.util
import pathlib
import sys
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app" / "soundblaster_zse_control.py"
INSTALL = (ROOT / "install.sh").read_text()
APP_TEXT = APP_PATH.read_text()


class V3339StaleTargetTests(unittest.TestCase):
    def test_version_bumped(self):
        self.assertIn('VERSION = "3.3.7"', APP_TEXT)
        self.assertIn('VERSION="3.3.7"', INSTALL)

    def test_installer_promotes_only_live_exact_surround_sibling(self):
        self.assertIn('SURROUND_SIBLING="${TARGET/analog-stereo/analog-surround-51}"', INSTALL)
        self.assertIn('$2 == n {found=1} END {exit !found}', INSTALL)
        self.assertIn('TARGET="$SURROUND_SIBLING"', INSTALL)

    def test_generator_resolves_stale_target_before_writing(self):
        block = APP_TEXT[APP_TEXT.index('if "--generate-eq-config" in sys.argv:'):]
        self.assertIn('_target = resolve_live_surround_sibling(_target)', block)
        self.assertLess(
            block.index('_target = resolve_live_surround_sibling(_target)'),
            block.index('_output.write_text(eq_config_text('),
        )

    def test_helper_behavior_matches_gjohnz_failure(self):
        # Load just enough of the module to exercise the pure routing helper
        # without opening the Tk GUI. The module exits early on --version.
        old_argv = sys.argv[:]
        try:
            sys.argv = [str(APP_PATH), "--version"]
            spec = importlib.util.spec_from_file_location("sb_v3339_test", APP_PATH)
            module = importlib.util.module_from_spec(spec)
            with self.assertRaises(SystemExit):
                spec.loader.exec_module(module)
        finally:
            sys.argv = old_argv

        stale = 'alsa_output.pci-0000_04_00.0.analog-stereo'
        surround = 'alsa_output.pci-0000_04_00.0.analog-surround-51'
        with mock.patch.object(module, 'sink_exists', side_effect=lambda name: name == surround):
            self.assertEqual(module.resolve_live_surround_sibling(stale), surround)
        with mock.patch.object(module, 'sink_exists', return_value=False):
            self.assertEqual(module.resolve_live_surround_sibling(stale), stale)
        ac3 = 'alsa_output.pci-0000_04_00.0.iec958-ac3-surround-51'
        with mock.patch.object(module, 'sink_exists') as exists:
            self.assertEqual(module.resolve_live_surround_sibling(ac3), ac3)
            exists.assert_not_called()


if __name__ == '__main__':
    unittest.main()
