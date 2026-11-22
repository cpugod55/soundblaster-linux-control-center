import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'install.sh').read_text()
class V3341A52PersistenceTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION="3.3.7"', INSTALL)
    def test_digital_device_number_parsed_from_aplay(self):
        self.assertIn("sed -nE 's/^card ([0-9]+): Creative .*device ([0-9]+): .*Digital.*/\\1 \\2/p'", INSTALL)
        self.assertIn('SB_ALSA_DEV="${SB_ALSA_PAIR#* }"', INSTALL)
        self.assertNotIn('gsub(":","",$6)', INSTALL)
    def test_pipewire_config_has_single_escaped_quotes_after_heredoc(self):
        # The shell source intentionally contains two backslashes before each quote;
        # an unquoted heredoc collapses them to one, yielding valid \" inside the PipeWire string.
        line=next(x for x in INSTALL.splitlines() if 'module-alsa-sink device=plug:{SLAVE=' in x)
        marker='SLAVE='
        tail=line.split(marker,1)[1]
        self.assertTrue(tail.startswith('\\\\"a52:'), repr(tail[:16]))
        self.assertFalse(tail.startswith('\\\\\\"a52:'), repr(tail[:16]))
    def test_explicit_digital_51_never_falls_back_to_analog(self):
        self.assertIn('Digital 5.1 was explicitly requested', INSTALL)
        self.assertIn('will not silently fall back to an analog output', INSTALL)
        self.assertRegex(INSTALL, r'if \[\[ "\$SPEAKER_LAYOUT" == "5\.1" && -z "\$TARGET" \]\]')
if __name__=='__main__': unittest.main()
