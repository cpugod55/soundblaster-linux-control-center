from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app/soundblaster_zse_control.py").read_text()

class MintRuntimeCompatibilityTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)

    def test_pw_record_raw_is_capability_detected(self):
        self.assertIn('def pw_record_supports_raw():', APP)
        self.assertIn('if pw_record_supports_raw():', APP)
        self.assertIn('cmd.append("--raw")', APP)
        meter = APP[APP.index('def _start_physical_port_meter'):APP.index('def _stop_analyzer_processes')]
        self.assertNotIn('["pw-record", "--raw"', meter)

    def test_fill_maintenance_is_not_on_tk_poll(self):
        self.assertIn('def fill_route_maintenance_worker():', APP)
        self.assertIn('wait_for_lock=False', APP)
        poll = APP[APP.index('def update_connection_status():'):APP.index('def analyzer_source_name():')]
        self.assertNotIn('route_speaker_fill_streams(', poll)

    def test_fill_route_has_collision_guard(self):
        self.assertIn('fill_route_lock = threading.Lock()', APP)
        self.assertIn('fill_route_lock.acquire(blocking=wait_for_lock)', APP)
        self.assertIn('fill_route_lock.release()', APP)

if __name__ == '__main__':
    unittest.main()
