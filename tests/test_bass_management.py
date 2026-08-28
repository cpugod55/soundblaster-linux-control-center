import ast
import cmath
import math
import unittest
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "soundblaster_zse_control.py"


def load_defs():
    tree = ast.parse(APP_SOURCE.read_text(), filename=str(APP_SOURCE))
    assignments = {"BANDS", "MAIN_BASS_POSITIONS", "BASS_SUM_GAIN", "DEFAULT_CURRENT", "APP_NAME", "APP_ID", "SINK"}
    functions = {"layout_name", "bass_dsp_controls", "ubuntu_bass_eq_graph", "eq_config_text"}
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            body.append(node)
    ns = {"math": math, "is_bazzite": lambda: False, "sink_channel_positions": lambda _: ["FL", "FR"]}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(APP_SOURCE), "exec"), ns)
    return ns


def biquad_magnitude(kind, freq, cutoff, q):
    w0 = 2 * math.pi * cutoff / 48000.0
    alpha = math.sin(w0) / (2 * q)
    c = math.cos(w0)
    if kind == "lp":
        b0, b1, b2 = (1-c)/2, 1-c, (1-c)/2
    else:
        b0, b1, b2 = (1+c)/2, -(1+c), (1+c)/2
    a0, a1, a2 = 1+alpha, -2*c, 1-alpha
    z = cmath.exp(-2j * math.pi * freq / 48000.0)
    return abs((b0+b1*z+b2*z*z) / (a0+a1*z+a2*z*z))


class BassManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_defs()
        cls.base = {"bass_management": True, "bass_routing": "REDIRECT", "bass_crossover": 80,
                    "bass_slope": "24", "lfe_trim": 0.0}

    def controls(self, **updates):
        return self.ns["bass_dsp_controls"]({**self.base, **updates})

    def test_modes_route_only_as_intended(self):
        off = self.controls(bass_management=False)
        lfe_only = self.controls(bass_routing="LFE_ONLY")
        redirect = self.controls(bass_routing="REDIRECT")
        duplicate = self.controls(bass_routing="DUPLICATE")
        for pos in self.ns["MAIN_BASS_POSITIONS"]:
            self.assertEqual(off[f"main_select_{pos}:Gain 1"], 1.0)
            self.assertEqual(lfe_only[f"bass_select_{pos}:Gain 2"], 0.0)
            self.assertEqual(redirect[f"main_select_{pos}:Gain 3"], 1.0)
            self.assertAlmostEqual(redirect[f"bass_select_{pos}:Gain 2"], 1/math.sqrt(5))
            self.assertEqual(duplicate[f"main_select_{pos}:Gain 1"], 1.0)
            self.assertAlmostEqual(duplicate[f"bass_select_{pos}:Gain 2"], 1/math.sqrt(5))

    def test_crossover_and_slope_have_measurably_different_responses(self):
        lp60 = biquad_magnitude("lp", 100, 60, 0.5)
        lp120 = biquad_magnitude("lp", 100, 120, 0.5)
        self.assertGreater(20 * math.log10(lp120/lp60), 6.5)
        hp12 = biquad_magnitude("hp", 40, 80, 0.5)
        hp24 = biquad_magnitude("hp", 40, 80, 2**-0.5) ** 2
        self.assertLess(20 * math.log10(hp24/hp12), -7.0)

    def test_lfe_trim_changes_native_lfe_only(self):
        zero, minus12 = self.controls(lfe_trim=0), self.controls(lfe_trim=-12)
        changed = {k for k in zero if abs(zero[k] - minus12[k]) > 1e-12}
        self.assertEqual(changed, {"native_lfe_trim:Mult"})
        self.assertAlmostEqual(20 * math.log10(minus12["native_lfe_trim:Mult"]), -12.0)

    def test_equal_power_sum_and_worst_case_headroom(self):
        gain = self.ns["BASS_SUM_GAIN"]
        self.assertAlmostEqual(gain, 1/math.sqrt(5))
        self.assertAlmostEqual(20*math.log10(math.sqrt(5)*gain), 0.0, places=9)
        self.assertAlmostEqual(20*math.log10(gain), -6.989700043, places=6)
        self.assertAlmostEqual(20*math.log10(1+5*gain), 10.200352718, places=6)

    def test_ubuntu_graph_is_explicit_and_bazzite_remains_duplicated(self):
        gains = {f: 0.0 for f in self.ns["BANDS"]}
        ubuntu = self.ns["eq_config_text"]("target", gains, ["FL","FR","RL","RR","FC","LFE"],
            0.0, self.base, compatibility=False)
        bazzite = self.ns["eq_config_text"]("target", gains, ["FL","FR","RL","RR","FC","LFE"],
            0.0, self.base, compatibility=True)
        self.assertIn('input = "lfe_sum:In 6"', ubuntu)
        self.assertIn('outputs = [ "main_select_FL:Out"', ubuntu)
        self.assertIn("name = native_lfe_trim", ubuntu)
        self.assertIn("name = lfe_limiter", ubuntu)
        self.assertNotIn("name = preamp_FL", bazzite)
        self.assertNotIn("name = lfe_sum", bazzite)


if __name__ == "__main__":
    unittest.main()
