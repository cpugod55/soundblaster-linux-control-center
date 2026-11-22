import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTROL = (ROOT / "app" / "soundblaster_zse_control.py").read_text(encoding="utf-8")
HELPER = (ROOT / "app" / "relaunch_helper.py").read_text(encoding="utf-8")


class V3365RelaunchGuardTests(unittest.TestCase):
    def test_apply_button_is_named_and_disabled_immediately(self):
        self.assertIn('apply_output_button=ttk.Button', CONTROL)
        self.assertIn('apply_output_button.state(["disabled"])', CONTROL)

    def test_relaunch_helper_writes_cross_instance_cooldown_marker(self):
        self.assertIn('COOLDOWN_PATH = RUNTIME_DIR / f"{APP_ID}-relaunch-cooldown"', HELPER)
        self.assertIn('COOLDOWN_PATH.write_text', HELPER)

    def test_relaunched_gui_honors_guard_window(self):
        self.assertIn('guard_seconds=4.0', CONTROL)
        self.assertIn('_apply_output_startup_guard()', CONTROL)

    def test_helper_serializes_sensitive_launch_window(self):
        self.assertIn('time.sleep(3.0)', HELPER)


if __name__ == "__main__":
    unittest.main()
