import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "install.sh").read_text()


class AnalogTargetRefreshTests(unittest.TestCase):
    def test_analog_profile_switch_resolves_new_sink_before_stale_fallback(self):
        analog = INSTALL.index('# For explicit analog layouts, select the matching advertised Creative profile.')
        stale = INSTALL.index('# Preserve an existing filter target if possible.')
        block = INSTALL[analog:stale]
        self.assertIn('WANT_SINK_SUFFIX="analog-surround-51"', block)
        self.assertIn('pactl list short sinks', block)
        self.assertIn('TARGET="$(pactl list short sinks', block)
        self.assertIn('Using Creative Analog target:', block)

    def test_analog_sink_resolution_is_scoped_to_creative_card(self):
        analog = INSTALL.index('# For explicit analog layouts, select the matching advertised Creative profile.')
        stale = INSTALL.index('# Preserve an existing filter target if possible.')
        block = INSTALL[analog:stale]
        self.assertIn('SB_PCI="${SB_CARD#alsa_card.}"', block)
        self.assertIn('-v pci="$SB_PCI"', block)


if __name__ == "__main__":
    unittest.main()
