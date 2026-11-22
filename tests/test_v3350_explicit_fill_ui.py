import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "soundblaster_zse_control.py").read_text()
INSTALL = (ROOT / "install.sh").read_text()


class V3350ExplicitFillAndUiTests(unittest.TestCase):
    def test_version_stamps(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
        self.assertIn("data['version']='3.3.7'", INSTALL)

    def test_explicit_a52_fill_graph_exists(self):
        self.assertIn('FILL_DSP_CONFIG = CONFIG_HOME / "pipewire/filter-chain.conf.d/soundblaster-zse-fill-dsp.conf"', APP)
        self.assertIn('def uses_explicit_fill_dsp(settings=None):', APP)
        self.assertIn('target == "alsa_output.soundblaster_a52_51"', APP)
        self.assertIn('or "iec958-ac3-surround-51" in target', APP)
        self.assertIn('name = front_l label = mixer', APP)
        self.assertIn('name = rear_delay_l label = delay', APP)
        self.assertIn('name = lfe_lp label = bq_lowpass', APP)
        self.assertIn('outputs = [ "front_l:Out" "front_r:Out" "rear_delay_l:Out" "rear_delay_r:Out" "center:Out" "lfe_lp:Out" ]', APP)
        self.assertIn('target.object = "{SINK}"', APP)
        self.assertIn('stream.dont-remix = true', APP)

    def test_modes_are_our_own_dsp_not_channelmix(self):
        self.assertIn('"rear_l:Gain 1": 0.75', APP)
        self.assertIn('"rear_l:Gain 1": 0.50, "rear_l:Gain 2": -0.50', APP)
        self.assertIn('"center:Gain 1": 0.5 if on else 0.0', APP)
        self.assertIn('"lfe_sum:Gain 1": 0.5 if on else 0.0', APP)
        self.assertIn('"rear_delay_l:Delay (s)": delay_s', APP)
        self.assertIn('"lfe_lp:Freq": cutoff', APP)

    def test_explicit_controls_are_live_and_persisted(self):
        self.assertIn('def set_fill_filter_controls(settings):', APP)
        self.assertRegex(APP, r'pw-cli", "s", str\(node_id\), "Props", payload')
        self.assertIn('FILL_DSP_CONFIG.write_text(fill_dsp_config_text(s))', APP)
        self.assertIn('return route_speaker_fill_streams(settings, force_restart=False)', APP)

    def test_upgrade_kills_legacy_fill_loopback_before_loading_explicit_graph(self):
        self.assertIn('def explicit_fill_graph_live():', APP)
        self.assertIn('_kill_external_fill_loopback()', APP)
        self.assertIn('wait_for_sink_gone(FILL_SINK, 2.0)', APP)
        self.assertIn('not explicit_fill_graph_live() and restart_if_missing', APP)

    def test_bazzite_verified_path_is_preserved(self):
        block = APP[APP.index('def uses_explicit_fill_dsp'):APP.index('def uses_stable_fill_route')]
        self.assertIn('if is_bazzite():\n        return False', block)
        self.assertIn('pw-loopback", "--name=" + FILL_LOOP_NAME', APP)

    def test_amd_family_visual_refresh_is_present(self):
        self.assertIn('ACCENT = "#1597d4"', APP)
        self.assertIn('Audio Dashboard  •  EQ  •  Spatial DSP  •  Device Control', APP)
        self.assertIn('status_chip = tk.Frame(header', APP)
        self.assertIn('version_chip = tk.Label(header', APP)
        self.assertIn('accent = ACCENT', APP)

    def test_about_privacy_and_project_links_still_present(self):
        self.assertNotIn('@gmail.com', APP.lower())
        self.assertIn('https://github.com/cpugod55/soundblaster-linux-control-center', APP)
        self.assertIn('https://github.com/sponsors/cpugod55', APP)


if __name__ == '__main__':
    unittest.main()
