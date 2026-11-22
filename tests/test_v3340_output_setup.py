import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'install.sh').read_text()
APP=(ROOT/'app'/'soundblaster_zse_control.py').read_text()
class V3340OutputSetupTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION="3.3.7"', INSTALL); self.assertIn('VERSION = "3.3.7"', APP)
    def test_connection_and_layout_options(self):
        self.assertIn('--connection) CONNECTION=', INSTALL); self.assertIn('--layout) SPEAKER_LAYOUT=', INSTALL)
        self.assertIn('auto|analog|digital', INSTALL); self.assertIn('auto|stereo|2.1|4.0|4.1|5.0|5.1', INSTALL)
    def test_arch_a52_package_detection_does_not_require_aplay_listing(self):
        self.assertIn("pacman -Q alsa-plugins", INSTALL); self.assertIn("libasound_module_pcm_a52.so", INSTALL)
    def test_cachyos_a52_sink_is_discovered_not_hardcoded(self):
        self.assertIn('SB_ALSA_CARD=', INSTALL); self.assertIn('SB_ALSA_DEV=', INSTALL)
        self.assertIn('alsa_output.soundblaster_a52_51', INSTALL); self.assertIn('module-alsa-sink', INSTALL)
    def test_unrelated_stale_target_is_rejected(self):
        self.assertIn('Ignoring stale target from another audio device', INSTALL); self.assertIn('TARGET=""', INSTALL)
    def test_atomic_and_live_usb_guidance(self):
        self.assertGreaterEqual(INSTALL.count('ACTION REQUIRED'), 2); self.assertIn('sudo pacman -Sy', INSTALL); self.assertIn('sudo rpm-ostree install', INSTALL)
if __name__=='__main__': unittest.main()
