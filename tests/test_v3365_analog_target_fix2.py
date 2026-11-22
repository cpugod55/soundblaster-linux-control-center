from pathlib import Path
import unittest

INSTALL = (Path(__file__).resolve().parents[1] / "install.sh").read_text()

class AnalogTargetFix2Tests(unittest.TestCase):
    def test_explicit_analog_never_reuses_digital_target(self):
        self.assertIn('Explicit Analog setup must never fall back to a preserved Digital/AC3 target.', INSTALL)
        self.assertIn('if [[ "$CONNECTION" == "analog" && -n "$SB_CARD" ]]; then', INSTALL)
        self.assertIn('5.1|auto) WANT_ANALOG_SUFFIX="analog-surround-51"', INSTALL)
        self.assertIn('TARGET="$ANALOG_TARGET"', INSTALL)
        self.assertIn('The installer will not reuse a stale Digital/AC3 EQ target.', INSTALL)

    def test_enforcement_occurs_after_preserved_target_read(self):
        preserve = INSTALL.index('# Preserve an existing filter target if possible.')
        enforce = INSTALL.index('# Explicit Analog setup must never fall back to a preserved Digital/AC3 target.')
        generate = INSTALL.index('--generate-eq-config')
        self.assertLess(preserve, enforce)
        self.assertLess(enforce, generate)

if __name__ == '__main__':
    unittest.main()
