import ast
import cmath
import json
import math
import tempfile
import unittest
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "soundblaster_zse_control.py"


def load_state_functions(state_dir):
    """Load the application's real state/headroom functions without starting Tk."""
    tree = ast.parse(APP_SOURCE.read_text(), filename=str(APP_SOURCE))
    assignments = {"VERSION", "BANDS", "DEFAULT_CURRENT", "DEFAULT_DATA"}
    functions = {
        "deep_default", "load_data", "save_data", "combined_eq_peak_db",
        "safe_preamp_limit", "effective_preamp_db", "percent_to_pactl_volume",
        "legacy_channel_db_to_percent",
    }
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & assignments:
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            body.append(node)
    namespace = {
        "cmath": cmath, "json": json, "math": math, "Path": Path,
        "STATE_DIR": state_dir, "STATE_FILE": state_dir / "state.json",
    }
    exec(compile(ast.Module(body=body, type_ignores=[]), str(APP_SOURCE), "exec"), namespace)
    return namespace


class StateHeadroomRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ns = load_state_functions(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def save_and_reload(self, current):
        data = self.ns["deep_default"]()
        data["current"].update(current)
        self.ns["save_data"](data)
        return self.ns["load_data"]()["current"]

    def test_non_flat_eq_survives_and_preserves_headroom_target(self):
        curve = {str(f): 0.0 for f in self.ns["BANDS"]}
        curve.update({"31": 13.0, "62": 12.5, "4000": 2.5, "8000": 6.5, "16000": 9.0})
        current = {"eq": curve, "preamp": 0.0, "safe_headroom": True}
        before_db = self.ns["effective_preamp_db"](current)
        loaded = self.save_and_reload(current)
        after_db = self.ns["effective_preamp_db"](loaded)
        self.assertEqual(loaded["eq"], curve)
        self.assertAlmostEqual(after_db, before_db, places=9)
        self.assertAlmostEqual(10.0 ** (after_db / 20.0), 10.0 ** (before_db / 20.0), places=9)
        self.assertLess(after_db, 0.0)

    def test_flat_eq_has_unity_safe_headroom_target(self):
        curve = {str(f): 0.0 for f in self.ns["BANDS"]}
        loaded = self.save_and_reload({"eq": curve, "preamp": 0.0, "safe_headroom": True})
        self.assertEqual(loaded["eq"], curve)
        self.assertAlmostEqual(self.ns["effective_preamp_db"](loaded), 0.0, places=9)

    def test_safe_headroom_off_uses_requested_preamp(self):
        curve = {str(f): 12.0 for f in self.ns["BANDS"]}
        loaded = self.save_and_reload({"eq": curve, "preamp": -2.5, "safe_headroom": False})
        self.assertEqual(loaded["eq"], curve)
        self.assertAlmostEqual(self.ns["effective_preamp_db"](loaded), -2.5, places=9)

    def test_channel_percent_uses_os_style_absolute_pactl_volume(self):
        convert = self.ns["percent_to_pactl_volume"]
        self.assertEqual(convert(100.0), 65536)
        self.assertEqual(convert(50.0), 32768)
        self.assertEqual(convert(0.0), 0)
        self.assertEqual(convert(120.0), 65536)

    def test_legacy_channel_db_migrates_without_boost(self):
        convert = self.ns["legacy_channel_db_to_percent"]
        self.assertAlmostEqual(convert(-12.0), 63.0957, places=3)
        self.assertEqual(convert(0.0), 100.0)
        self.assertEqual(convert(12.0), 100.0)


if __name__ == "__main__":
    unittest.main()

class MeterLevelRegressionTests(unittest.TestCase):
    def test_meter_level_tracks_os_style_channel_percent(self):
        tree = ast.parse(APP_SOURCE.read_text(), filename=str(APP_SOURCE))
        funcs = {"meter_db_after_channel_level"}
        body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in funcs]
        ns = {"math": math}
        exec(compile(ast.Module(body=body, type_ignores=[]), str(APP_SOURCE), "exec"), ns)
        f = ns["meter_db_after_channel_level"]
        self.assertAlmostEqual(f(-6.0, 100), -6.0, places=6)
        self.assertAlmostEqual(f(-6.0, 50), -12.0205999, places=4)
        self.assertEqual(f(-6.0, 0), -60.0)
