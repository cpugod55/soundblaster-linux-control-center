from pathlib import Path
import ast
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app/soundblaster_zse_control.py"
APP=APP_PATH.read_text()
INSTALL=(ROOT/"install.sh").read_text()

class MintFillRecreateTests(unittest.TestCase):
    def test_version(self):
        self.assertIn('VERSION = "3.3.7"', APP)
        self.assertIn('APP_VERSION="3.3.7"', INSTALL)
    def test_old_pipewire_is_version_driven(self):
        self.assertIn('def pipewire_version_tuple():', APP)
        self.assertIn('def fill_live_channelmix_needs_recreate():', APP)
        self.assertIn('version < (1, 2, 0)', APP)
    def test_spatial_recreates_when_signature_changes(self):
        b=APP[APP.index('def live_set_spatial(settings):'):APP.index('def _apply_spatial_live():')]
        self.assertIn('FILL_SIGNATURE != requested', b)
        self.assertIn('force_restart=force_restart', b)
    def test_waits_for_old_sink_to_disappear(self):
        self.assertIn('def wait_for_sink_gone(name, timeout=2.0):', APP)
        b=APP[APP.index('def start_fill_loopback'):APP.index('def route_speaker_fill_streams')]
        self.assertIn('wait_for_sink_gone(FILL_SINK, 2.0)', b)
    def test_cinnamon_busy_cursor_fix(self):
        self.assertIn('StartupNotify=false', INSTALL)
    def _compat(self, version):
        tree=ast.parse(APP)
        body=[]
        for n in tree.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_PIPEWIRE_VERSION_CACHE' for t in n.targets): body.append(n)
            if isinstance(n,ast.FunctionDef) and n.name in {'pipewire_version_tuple','fill_live_channelmix_needs_recreate'}: body.append(n)
        class R:
            stderr=''
            returncode=0
            def __init__(self,s): self.stdout=s
        ns={'re':__import__('re'),'run':lambda *a,**k:R('pipewire\nCompiled with libpipewire '+version+'\n')}
        exec(compile(ast.Module(body=body,type_ignores=[]),'<test>','exec'),ns)
        return ns['fill_live_channelmix_needs_recreate']()
    def test_pipewire_1_0_recreates(self): self.assertTrue(self._compat('1.0.5'))
    def test_pipewire_1_6_keeps_live_path(self): self.assertFalse(self._compat('1.6.8'))

if __name__=='__main__': unittest.main()
