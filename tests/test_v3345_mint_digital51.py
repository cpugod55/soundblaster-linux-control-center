import pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (ROOT / 'install.sh').read_text()
APP = (ROOT / 'app' / 'soundblaster_zse_control.py').read_text()


class V3345MintDigital51Tests(unittest.TestCase):
    def test_version_stamp(self):
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn("data['version']='3.3.7'", INSTALL)

    def test_debian_package_presence_counts_as_a52(self):
        self.assertIn('have_a52_deb_package()', INSTALL)
        self.assertIn('dpkg-query -W', INSTALL)
        self.assertIn('libasound2-plugins', INSTALL)
        self.assertIn('have_a52_deb_package || have_a52_runtime', INSTALL)

    def test_debian_family_enters_persistent_a52_path(self):
        self.assertIn('command -v dpkg-query >/dev/null 2>&1 ||', INSTALL)
        self.assertIn('$USE_PERSISTENT_A52 -eq 1', INSTALL)
        self.assertIn('alsa_output.soundblaster_a52_51', INSTALL)

    def test_native_ac3_profile_is_preferred_when_available(self):
        native = INSTALL.index('Prefer a native Creative AC3 5.1 profile')
        compat = INSTALL.index('USE_PERSISTENT_A52=0')
        self.assertLess(native, compat)
        self.assertIn('output:iec958-ac3-surround-51+input:analog-stereo', INSTALL)
        self.assertIn('Using native Creative Digital AC3 5.1 profile', INSTALL)
        self.assertIn('-z "$TARGET" && "$CONNECTION" == "digital"', INSTALL)

    def test_mint_iec958_and_dynamic_pcm_are_automatic(self):
        self.assertIn('amixer -c "$SB_ALSA_CARD" set IEC958 unmute', INSTALL)
        self.assertIn("sed -nE 's/^card ([0-9]+): Creative .*device ([0-9]+): .*Digital.*/\\1 \\2/p'", INSTALL)
        self.assertNotIn('hw:2,1', INSTALL)

    def test_explicit_digital_51_is_fail_closed_before_generic_target_selection(self):
        guard = INSTALL.index('Explicit Digital + 5.1 is fail-closed')
        generic = INSTALL.index('# Preserve an existing filter target if possible.')
        self.assertLess(guard, generic)
        self.assertIn('will not silently fall back to an analog output or another audio device', INSTALL)

    def test_live_cdrom_source_repair_is_scoped_and_backed_up(self):
        self.assertIn("grep -Eq '^[[:space:]]*deb[[:space:]]+cdrom:'", INSTALL)
        self.assertIn('${src}.soundblaster-backup', INSTALL)
        self.assertIn('Disabled stale APT cdrom source(s) from the Live environment', INSTALL)
        self.assertIn('sudo apt-get update', INSTALL)


if __name__ == '__main__':
    unittest.main()
