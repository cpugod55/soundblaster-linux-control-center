import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'install.sh').read_text()
class V3342A52DeviceReleaseTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION="3.3.7"', INSTALL)
    def test_digital_a52_releases_normal_creative_profile_first(self):
        off='pactl set-card-profile "$SB_CARD" off'
        restart='systemctl --user restart pipewire-pulse.service'
        self.assertIn(off, INSTALL)
        self.assertLess(INSTALL.index(off), INSTALL.index(restart, INSTALL.index(off)))
        self.assertIn('Device or resource busy', INSTALL)
    def test_a52_failure_restores_previous_profile(self):
        self.assertIn('SB_PROFILE_BEFORE_A52="$SB_ACTIVE_PROFILE"', INSTALL)
        self.assertIn('pactl set-card-profile "$SB_CARD" "$SB_PROFILE_BEFORE_A52"', INSTALL)
    def test_success_keeps_a52_target(self):
        self.assertIn('TARGET="alsa_output.soundblaster_a52_51"', INSTALL)
        self.assertIn('will not silently fall back to an analog output', INSTALL)
if __name__=='__main__': unittest.main()
