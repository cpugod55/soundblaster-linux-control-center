import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "install.sh").read_text()
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()


class V3353OpenSuseDebianInstallerTests(unittest.TestCase):
    def test_version_stamps(self):
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn("data['version']='3.3.7'", INSTALL)

    def test_zypper_is_supported(self):
        self.assertIn('install_opensuse_deps()', INSTALL)
        self.assertIn('sudo zypper --non-interactive install "${need[@]}"', INSTALL)
        self.assertIn('need+=(python3-tk)', INSTALL)
        self.assertIn('need+=(alsa-plugins-a52)', INSTALL)
        self.assertIn('need+=(ladspa-zam-plugins)', INSTALL)

    def test_opensuse_a52_does_not_depend_on_aplay_L_hint(self):
        self.assertIn('command -v zypper >/dev/null 2>&1 ||', INSTALL)
        self.assertIn('device=plug:a52:${SB_ALSA_CARD}', INSTALL)
        self.assertIn('Digital AC3 5.1 target created from openSUSE A52 PCM plug:a52:${SB_ALSA_CARD}', INSTALL)

    def test_both_creative_iec958_switches_are_unmuted(self):
        self.assertIn('set IEC958 unmute', INSTALL)
        self.assertIn("set 'IEC958 Default PCM' unmute", INSTALL)

    def test_existing_non_opensuse_a52_device_string_is_preserved(self):
        self.assertIn('device=plug:{SLAVE=\\\\"a52:${SB_ALSA_CARD},\'hw:${SB_ALSA_CARD},${SB_ALSA_DEV}\'\\\\"}', INSTALL)

    def test_debian_audio_readiness_is_checked_before_pactl_card_detection(self):
        ready = INSTALL.index('ensure_debian_audio_ready')
        detect = INSTALL.index('PACTL_CARDS="$(pactl list cards')
        self.assertLess(ready, detect)
        self.assertIn('systemctl --user start pipewire.socket pipewire-pulse.socket', INSTALL)
        self.assertIn('PipeWire-Pulse is installed but pactl still cannot connect', INSTALL)

    def test_pactl_failure_has_explicit_diagnostic(self):
        self.assertIn('pactl cannot connect to PipeWire-Pulse, so Sound Blaster hardware cannot be detected', INSTALL)

    def test_debian_dependency_list_is_deduplicated(self):
        self.assertIn("awk '!seen[$0]++'", INSTALL)


if __name__ == '__main__':
    unittest.main()
