import ast
import unittest
from pathlib import Path

APP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "soundblaster_zse_control.py"


def load_defs():
    tree = ast.parse(APP_SOURCE.read_text(), filename=str(APP_SOURCE))
    assignments = {"BANDS", "DEFAULT_CURRENT"}
    functions = {"fill_config_text", "pulse_channel_map", "reorder_meter_levels"}
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            body.append(node)
    ns = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(APP_SOURCE), "exec"), ns)
    return ns


class SpatialRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_defs()

    def test_fill_off_persists_upmix_false(self):
        text = self.ns["fill_config_text"]({**self.ns["DEFAULT_CURRENT"], "fill_mode": "OFF"}, compatibility=False)
        self.assertIn("channelmix.upmix = false", text)

    def test_meter_reorder_maps_native_monitor_order_to_display_order(self):
        native = ["FL", "FR", "RL", "RR", "FC", "LFE"]
        display = ["FL", "FR", "FC", "LFE", "RL", "RR"]
        values = [-5.0, -10.0, -15.0, -20.0, -25.0, -30.0]
        self.assertEqual(
            self.ns["reorder_meter_levels"](values, native, display),
            [-5.0, -10.0, -25.0, -30.0, -15.0, -20.0],
        )

    def test_native_pulse_map_uses_detected_order(self):
        native = ["FL", "FR", "RL", "RR", "FC", "LFE"]
        self.assertEqual(
            self.ns["pulse_channel_map"](native),
            "front-left,front-right,rear-left,rear-right,front-center,lfe",
        )


if __name__ == "__main__":
    unittest.main()
