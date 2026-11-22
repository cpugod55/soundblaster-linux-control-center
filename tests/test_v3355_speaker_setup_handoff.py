import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app/soundblaster_zse_control.py').read_text()

class V3355SpeakerSetupHandoffTests(unittest.TestCase):
    def test_fill_engine_is_on_spatial_page(self):
        spatial = APP.index('# ---------- Spatial / Fill ----------')
        speaker = APP.index('# ---------- Speaker Setup ----------')
        selector = APP.index('text="Fill Engine"')
        self.assertTrue(spatial < selector < speaker)

    def test_engine_handoff_tears_down_explicit_graph(self):
        self.assertIn('def switch_fill_engine_live(settings):', APP)
        self.assertIn('if engine == "pipewire":', APP)
        self.assertIn('if FILL_DSP_CONFIG.exists():', APP)
        self.assertIn('FILL_DSP_CONFIG.unlink()', APP)
        self.assertIn('restart_filter_chain_service()', APP)
        self.assertIn('restart_pipewire_pulse_defaults()', APP)

    def test_application_disables_global_upmix(self):
        self.assertIn('write_spatial(s, compatibility=True)', APP)
        self.assertIn('compatibility=uses_stable_fill_route(s)', APP)

    def test_auto_connection_disables_layout(self):
        self.assertIn('is_auto = output_connection_var.get() == "auto"', APP)
        self.assertIn('layout_combo.configure(state="disabled" if is_auto else "readonly")', APP)
        self.assertIn('Auto-detected:', APP)

    def test_speaker_test_is_shortened(self):
        self.assertIn('root.after(700, lambda p=proc:', APP)
        self.assertNotIn('root.after(1400, lambda b=btn:', APP)

if __name__ == '__main__':
    unittest.main()
