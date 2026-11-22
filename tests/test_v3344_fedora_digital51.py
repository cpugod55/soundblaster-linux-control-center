import pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (ROOT / 'install.sh').read_text()

class V3344FedoraDigital51Tests(unittest.TestCase):
    def test_app_version_is_isolated_from_os_release(self):
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
        self.assertNotIn('\nVERSION="3.3.7"', INSTALL)
        self.assertIn('OS_ID="$(. /etc/os-release;', INSTALL)
        self.assertIn('OS_LIKE="$(. /etc/os-release;', INSTALL)
        self.assertNotIn('\n  . /etc/os-release\n', INSTALL)
        self.assertIn('Installed Sound Blaster Linux Control Center $APP_VERSION', INSTALL)

    def test_fedora_package_presence_counts_as_a52(self):
        self.assertIn('have_a52_package || have_a52_runtime', INSTALL)
        self.assertIn("rpm -q alsa-plugins-a52", INSTALL)

    def test_persistent_a52_path_includes_fedora_not_only_pacman(self):
        self.assertIn('USE_PERSISTENT_A52=0', INSTALL)
        self.assertIn('"$OS_ID" == "fedora"', INSTALL)
        self.assertIn('$USE_PERSISTENT_A52 -eq 1', INSTALL)
        self.assertNotIn('&& command -v pacman >/dev/null 2>&1 && have_a52; then', INSTALL)

    def test_creative_digital_pcm_is_dynamic(self):
        self.assertIn("sed -nE 's/^card ([0-9]+): Creative .*device ([0-9]+): .*Digital.*/\\1 \\2/p'", INSTALL)
        self.assertIn('SB_ALSA_CARD="${SB_ALSA_PAIR%% *}"', INSTALL)
        self.assertIn('SB_ALSA_DEV="${SB_ALSA_PAIR#* }"', INSTALL)
        self.assertNotIn('a52:2,', INSTALL)
        self.assertNotIn("hw:2,1", INSTALL)

    def test_iec958_switch_is_enabled_when_exposed(self):
        self.assertIn('amixer -c "$SB_ALSA_CARD" scontrols', INSTALL)
        self.assertIn("grep -Fq \"'IEC958',0\"", INSTALL)
        self.assertIn('amixer -c "$SB_ALSA_CARD" set IEC958 unmute', INSTALL)
        off = INSTALL.index('pactl set-card-profile "$SB_CARD" off')
        unmute = INSTALL.index('amixer -c "$SB_ALSA_CARD" set IEC958 unmute')
        self.assertLess(unmute, off)

    def test_explicit_digital_51_fails_closed(self):
        self.assertIn('Digital 5.1 was explicitly requested', INSTALL)
        self.assertIn('will not silently fall back to an analog output', INSTALL)

if __name__ == '__main__':
    unittest.main()
