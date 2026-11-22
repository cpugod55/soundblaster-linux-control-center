import ast
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[1] / 'app' / 'soundblaster_zse_control.py'

class TestHeadlessRestoreOrdering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(APP.read_text())
        cls.definitions = {node.name: i for i,node in enumerate(cls.tree.body)
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        cls.dispatch_index = next(i for i,node in enumerate(cls.tree.body)
                                  if isinstance(node,ast.If) and '--restore-selected' in ast.unparse(node.test))

    def test_headless_stream_functions_are_defined_before_dispatch(self):
        for name in ('restore_when_selected','_sink_id_name_map','playback_sink_inputs',
                     '_fill_output_id','update_fill_processing','uses_stable_fill_route',
                     'apply_bass_management_live','restore_live_eq_verified',
                     'restore_channel_levels_verified','restore_preamp_verified'):
            with self.subTest(name=name):
                self.assertLess(self.definitions[name],self.dispatch_index)

    def test_fill_processing_failure_not_reported_as_success(self):
        body = ast.get_source_segment(APP.read_text(), next(n for n in self.tree.body
                                    if isinstance(n, ast.FunctionDef) and n.name=='restore_when_selected'))
        self.assertIn('fill_updated = update_fill_processing(current)',body)
        self.assertIn('ok = False',body)
        self.assertIn('Speaker Fill controls unavailable',body)
