import ast
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app" / "soundblaster_zse_control.py"
APP = APP_PATH.read_text()


def load_graph_defs(is_bazzite_value=False):
    tree = ast.parse(APP, filename=str(APP_PATH))
    assignments = {"BANDS", "MAIN_BASS_POSITIONS", "BASS_SUM_GAIN", "DEFAULT_CURRENT", "APP_NAME", "APP_ID", "SINK"}
    functions = {"layout_name", "bass_dsp_controls", "ubuntu_bass_eq_graph", "eq_config_text"}
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
            body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            body.append(node)
    ns = {
        "math": math,
        "is_bazzite": lambda: is_bazzite_value,
        "filter_channel_positions": lambda _: ["FL", "FR", "RL", "RR", "FC", "LFE"],
    }
    exec(compile(ast.Module(body=body, type_ignores=[]), str(APP_PATH), "exec"), ns)
    return ns


class A52SpatialBassRegressionTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

    def test_dedicated_fill_playback_allows_channelmix(self):
        self.assertIn('stream.dont-remix = false', APP)
        self.assertNotIn('node.passive = true stream.dont-remix = true', APP)
        self.assertIn('channelmix.upmix = {str(enabled).lower()}', APP)
        self.assertIn('channelmix.rear-delay', APP)
        self.assertIn('channelmix.stereo-widen', APP)
        self.assertIn('channelmix.lfe-cutoff', APP)

    def test_a52_compatibility_routing_keeps_explicit_bass_graph(self):
        ns = load_graph_defs(False)
        settings = {
            "bass_management": True,
            "bass_routing": "REDIRECT",
            "bass_crossover": 80,
            "bass_slope": "24",
            "lfe_trim": 0.0,
        }
        cfg = ns["eq_config_text"](
            "alsa_output.soundblaster_a52_51",
            {f: 0.0 for f in ns["BANDS"]},
            ["FL", "FR", "RL", "RR", "FC", "LFE"],
            0.0,
            settings,
            compatibility=True,
        )
        self.assertIn('target.object = "alsa_output.soundblaster_a52_51"', cfg)
        self.assertIn('name = preamp_FL', cfg)
        self.assertIn('name = lfe_sum', cfg)
        self.assertIn('name = native_lfe_trim', cfg)
        self.assertIn('name = lfe_limiter', cfg)

    def test_bazzite_still_uses_legacy_compatibility_graph(self):
        ns = load_graph_defs(True)
        settings = {"bass_management": True, "bass_routing": "REDIRECT", "bass_crossover": 80, "bass_slope": "24", "lfe_trim": 0.0}
        cfg = ns["eq_config_text"](
            "target", {f: 0.0 for f in ns["BANDS"]},
            ["FL", "FR", "RL", "RR", "FC", "LFE"], 0.0, settings, compatibility=True)
        self.assertNotIn('name = preamp_FL', cfg)
        self.assertNotIn('name = lfe_sum', cfg)

    def test_persist_keeps_a52_compatibility_targeting(self):
        block = APP[APP.index('def persist_bass_management_config'):APP.index('def live_set_eq')]
        self.assertIn('compatibility=uses_dedicated_fill_route(settings)', block)


if __name__ == '__main__':
    unittest.main()
