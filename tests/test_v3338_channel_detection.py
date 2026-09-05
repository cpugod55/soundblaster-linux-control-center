import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / 'app' / 'soundblaster_zse_control.py').read_text()
INSTALL = (ROOT / 'install.sh').read_text()


class V3338ChannelDetectionTests(unittest.TestCase):
    def _load_helpers(self):
        ns = {'re': __import__('re')}
        start = APP.index('def normalize_channel_positions')
        end = APP.index('\ndef filter_channel_positions', start)
        exec(APP[start:end], ns)
        return ns

    def test_version_bumped(self):
        self.assertIn('VERSION = "3.3.38"', APP)
        self.assertIn('VERSION="3.3.38"', INSTALL)

    def test_literal_jameyr_quoted_layout_parses(self):
        ns = self._load_helpers()
        value = '[ "FL", "FR", "FC", "LFE", "RL", "RR" ]'
        self.assertEqual(
            ns['normalize_channel_positions'](value),
            ['FL', 'FR', 'FC', 'LFE', 'RL', 'RR'],
        )

    def test_best_candidate_ignores_stale_stereo_duplicate(self):
        ns = self._load_helpers()
        name = 'alsa_output.pci-0000_06_00.0.analog-surround-51'
        dump = [
            {
                'info': {'props': {
                    'node.name': name,
                    'media.class': 'Stream/Output/Audio',
                    'audio.channels': '2',
                    'audio.position': '[ FL FR ]',
                }}
            },
            {
                'info': {'props': {
                    'node.name': name,
                    'media.class': 'Audio/Sink',
                    'audio.channels': '6',
                    'audio.position': '[ "FL", "FR", "FC", "LFE", "RL", "RR" ]',
                }}
            },
        ]
        self.assertEqual(
            ns['_best_pw_dump_sink_layout'](dump, name),
            ['FL', 'FR', 'RL', 'RR', 'FC', 'LFE'],
        )

    def test_surround51_name_has_safe_canonical_fallback(self):
        self.assertIn('if "analog-surround-51" in lowered or "surround-51" in lowered:', APP)
        self.assertIn('if ("analog-surround-51" in target.lower() or "surround-51" in target.lower()):', INSTALL)

    def test_installer_does_not_break_on_first_matching_object(self):
        self.assertIn('candidates.append((score, channels, vals))', INSTALL)
        self.assertIn('max(candidates, key=lambda item: item[0])', INSTALL)


if __name__ == '__main__':
    unittest.main()
