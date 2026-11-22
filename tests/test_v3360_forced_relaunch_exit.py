from pathlib import Path
import unittest
APP=(Path(__file__).parents[1]/'app'/'soundblaster_zse_control.py').read_text()
class TestForcedRelaunchExit(unittest.TestCase):
    def test_output_apply_hard_exits_old_gui_after_cleanup(self):
        block=APP[APP.index('def apply_output_setup():'):APP.index('ttk.Label(setup_frame,text="Connection"')]
        self.assertIn('save_current_state()', block)
        self.assertIn('if SOCKET_PATH.exists(): SOCKET_PATH.unlink()', block)
        self.assertIn('os._exit(0)', block)
        self.assertNotIn('root.after(200, on_close)', block)
if __name__=='__main__': unittest.main()
