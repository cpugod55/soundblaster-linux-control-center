import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()


class UbuntuExplicitFillTests(unittest.TestCase):
    def test_version_stamps(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
        self.assertIn("data['version']='3.3.7'", INSTALL)

    def test_native_ubuntu_ac3_uses_explicit_fill(self):
        self.assertIn('or "iec958-ac3-surround-51" in target', APP)
        self.assertIn('target == "alsa_output.soundblaster_a52_51"', APP)

    def test_bazzite_explicit_fill_stays_disabled(self):
        block = APP[APP.index('def uses_explicit_fill_dsp'):APP.index('def fill_dsp_controls')]
        self.assertIn('if is_bazzite():\n        return False', block)

    def test_ubuntu_fill_routing_is_decoupled_from_eq_compatibility(self):
        self.assertIn('def uses_stable_fill_route(settings=None):', APP)
        self.assertIn('return uses_dedicated_fill_route(settings) or uses_explicit_fill_dsp(settings)', APP)
        self.assertIn('if uses_stable_fill_route(current) and sink_exists(SINK) and soundblaster_default_selected():', APP)
        self.assertIn('if uses_stable_fill_route(settings):', APP)
        # EQ compatibility remains tied to the existing dedicated A52/Bazzite path.
        self.assertIn('compatibility = uses_dedicated_fill_route(settings)', APP)

    def test_explicit_fill_topology_is_preserved(self):
        self.assertIn('"rear_l:Gain 1": 0.75', APP)
        self.assertIn('"center:Gain 1": 0.5 if on else 0.0', APP)
        self.assertIn('"lfe_sum:Gain 1": 0.5 if on else 0.0', APP)
        self.assertIn('outputs = [ "front_l:Out" "front_r:Out" "rear_delay_l:Out" "rear_delay_r:Out" "center:Out" "lfe_lp:Out" ]', APP)


if __name__ == '__main__':
    unittest.main()
