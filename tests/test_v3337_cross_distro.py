import importlib.util
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app" / "soundblaster_zse_control.py"
INSTALL = (ROOT / "install.sh").read_text()
APP = APP_PATH.read_text()


class V3337CrossDistroTests(unittest.TestCase):
    def test_version_bumped(self):
        self.assertIn('VERSION = "3.3.38"', APP)
        self.assertIn('VERSION="3.3.38"', INSTALL)

    def test_channel_position_parser_accepts_quoted_wireplumber_string(self):
        # Extract the function without importing the GUI module.
        ns = {"re": __import__("re")}
        start = APP.index("def normalize_channel_positions")
        end = APP.index("\ndef sink_channel_positions", start)
        exec(APP[start:end], ns)
        parsed = ns["normalize_channel_positions"]('[ "FL", "FR", "FC", "LFE", "RL", "RR" ]')
        self.assertEqual(parsed, ["FL", "FR", "FC", "LFE", "RL", "RR"])

    def test_virtual_eq_canonicalizes_complete_51_layout(self):
        self.assertIn('canonical_51 = ["FL", "FR", "RL", "RR", "FC", "LFE"]', APP)
        self.assertIn('if len(positions) == 6 and set(positions) == set(canonical_51):', APP)
        self.assertIn('positions = positions or filter_channel_positions(target_sink)', APP)

    def test_arch_and_fedora_install_zamaxim_packages(self):
        self.assertIn('need+=(zam-plugins-ladspa)', INSTALL)
        self.assertIn('need+=(ladspa-zam-plugins)', INSTALL)
        self.assertIn('missing+=(ladspa-zam-plugins)', INSTALL)

    def test_installer_has_targeted_ownership_repair(self):
        self.assertIn('check_user_config_path "$HOME/.config/pipewire"', INSTALL)
        self.assertIn('sudo chown -R', INSTALL)
        self.assertIn('Do not run this installer with sudo/root', INSTALL)

    def test_ca0132_mapping_fix_is_guarded_opt_in(self):
        self.assertIn('--ca0132-channel-fix', INSTALL)
        self.assertIn('CA0132_CHANNEL_FIX=0', INSTALL)
        self.assertIn('audio.position = [ "FL", "FR", "FC", "LFE", "RL", "RR" ]', INSTALL)
        self.assertIn('requires an analog-surround-51 target', INSTALL)

    def test_filter_chain_service_is_distro_neutral(self):
        self.assertIn('systemctl --user cat filter-chain.service', INSTALL)
        self.assertIn('systemctl --user is-active --quiet filter-chain.service', INSTALL)
        self.assertIn('def restart_filter_chain_service()', APP)
        helper = APP[APP.index('def restart_filter_chain_service'):APP.index('\ndef ensure_configs', APP.index('def restart_filter_chain_service'))]
        self.assertIn('reset-failed', helper)
        self.assertIn('restart", "filter-chain.service', helper)


if __name__ == "__main__":
    unittest.main()
