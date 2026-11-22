import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "app" / "audio_return_helper.py"
spec = importlib.util.spec_from_file_location("audio_return_helper", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestAudioReturnHelper(unittest.TestCase):
    def test_exact_card_and_virtual_sinks(self):
        target = "alsa_output.pci-0000_05_00.0.iec958-ac3-surround-51"
        for default in (target, "soundblaster_zse_eq", "soundblaster_zse_fill",
                        "alsa_output.pci-0000_05_00.0.iec958-stereo"):
            self.assertTrue(module.is_selected(default, target))
    def test_never_touch_unrelated_devices(self):
        target = "alsa_output.pci-0000_05_00.0.iec958-ac3-surround-51"
        for default in ("", "alsa_output.usb-Arctis.analog-stereo",
                        "alsa_output.pci-0000_03_00.0.iec958-stereo",
                        "bluez_output.AA_BB.a2dp-sink", "alsa_output.pci-0000_05_00.1.analog-stereo"):
            self.assertFalse(module.is_selected(default, target))
    def test_no_target_never_restores(self):
        self.assertFalse(module.is_selected("soundblaster_zse_eq", ""))
    def test_gui_open_skips(self):
        with patch.object(type(module.CONTROL), "exists", return_value=True), patch.object(module, "gui_running", return_value=True):
            self.assertFalse(module.recover())

class TestRoutingObservation(unittest.TestCase):
    def setUp(self):
        self.target = 'alsa_output.pci-0000_05_00.0.iec958-ac3-surround-51'
        self.sb = 'soundblaster_zse_eq'
        self.usb = 'alsa_output.usb-generic.analog-stereo'

    def test_detects_stream_migration_with_same_default(self):
        before = (self.sb, self.target, (('13', '221'),))
        self.assertTrue(module.observe(self.sb, self.target, (('13', '562539'),), before))

    def test_unrelated_default_never_repairs_even_when_streams_move(self):
        before = (self.usb, self.target, (('13', '221'),))
        self.assertFalse(module.observe(self.usb, self.target, (('13', '562539'),), before))

    def test_unchanged_state_no_repeat(self):
        before = (self.sb, self.target, (('13', '562539'),))
        self.assertFalse(module.observe(self.sb, self.target, (('13', '562539'),), before))

    def test_failed_probe_no_restore(self):
        self.assertFalse(module.observe(self.sb, self.target, None, None))

    def test_signature_identifies_sink_moves(self):
        from types import SimpleNamespace
        with patch.object(module, 'command', return_value=SimpleNamespace(returncode=0, stdout='13\t221\tprotocol-native.c\n14\t562539\tprotocol-native.c\n')):
            self.assertEqual(module.playback_signature(), (('13', '221'), ('14', '562539')))
