"""One-unit transport relocation: import compatibility and unchanged implementation."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from hf_payload.transport.presentation import presentation

class PresentationRelocationTests(unittest.TestCase):
    def child(self, code):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_relocated_implementation_bytes_unchanged(self):
        raw = (ROOT / 'src/hf_payload/transport/presentation.py').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '8135e2a8e6d1e2b6156dcdc55193749d577cdb568f2fdb97a025daa3e21bf5af')

    def test_legacy_exports_are_same_objects(self):
        import gui_presentation as legacy
        import hf_payload.transport.presentation as canonical
        self.assertIs(legacy.presentation, canonical.presentation)
        self.assertIs(legacy.DESKTOP, canonical.DESKTOP)
        self.assertIs(legacy.Counter, canonical.Counter)

    def test_gui_transport_uses_canonical_function(self):
        import gui_install
        self.assertIs(gui_install.presentation, presentation)
        source = (ROOT / 'tools/gui_install.py').read_text(encoding='utf-8')
        self.assertNotIn('from gui_presentation import', source)

    def test_src_only_import_without_tools(self):
        result = self.child('import sys,json;sys.path.insert(0,' + repr(str(ROOT / 'src')) + ');'
                            'from hf_payload.transport.presentation import presentation;'
                            'print(json.dumps(dict(module=presentation.__module__,legacy="gui_presentation" in sys.modules)))')
        self.assertEqual(result, dict(module='hf_payload.transport.presentation', legacy=False))

    def test_legacy_tools_only_source_import(self):
        result = self.child('import sys,json;sys.path.insert(0,' + repr(str(ROOT / 'tools')) + ');'
                            'import gui_presentation as old;'
                            'from hf_payload.transport.presentation import presentation;'
                            'print(json.dumps(dict(same=old.presentation is presentation)))')
        self.assertEqual(result, dict(same=True))

    def test_frozen_flag_with_bundle_only_does_not_add_source_paths(self):
        # Simulates package/module lookup, not a real PyInstaller build/bootloader.
        with tempfile.TemporaryDirectory(prefix='presentation-import-', dir=ROOT / 'out') as tmp:
            bundle = Path(tmp) / '_internal'
            package = bundle / 'hf_payload/transport'
            package.mkdir(parents=True)
            shutil.copyfile(ROOT / 'src/hf_payload/__init__.py', package.parent / '__init__.py')
            for name in ('__init__.py', 'presentation.py'):
                shutil.copyfile(ROOT / 'src/hf_payload/transport' / name, package / name)
            shutil.copyfile(ROOT / 'tools/gui_presentation.py', bundle / 'gui_presentation.py')
            result = self.child('import sys,json;sys.frozen=True;sys._MEIPASS=' + repr(str(bundle)) + ';'
                                'sys.path.insert(0,sys._MEIPASS);before=list(sys.path);'
                                'import gui_presentation as old;'
                                'import hf_payload.transport.presentation as new;'
                                'print(json.dumps(dict(same=old.presentation is new.presentation,'
                                'path_unchanged=sys.path==before,origin=new.__file__)))')
            self.assertTrue(result['same'])
            self.assertTrue(result['path_unchanged'])
            self.assertTrue(Path(result['origin']).is_relative_to(bundle))

    def test_only_stdlib_dependency_and_no_duplicate_function(self):
        canonical = ast.parse((ROOT / 'src/hf_payload/transport/presentation.py').read_text(encoding='utf-8'))
        imports = [n.module for n in ast.walk(canonical) if isinstance(n, ast.ImportFrom)]
        self.assertEqual(imports, ['collections'])
        wrapper = ast.parse((ROOT / 'tools/gui_presentation.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in ast.walk(wrapper)))
        self.assertEqual(sum(isinstance(n, ast.FunctionDef) and n.name == 'presentation'
                             for n in ast.walk(canonical)), 1)

    def test_static_freezer_import_edge_and_export_inputs(self):
        from release_config import source_export_plan
        rows = {r['path'] for r in source_export_plan(ROOT)}
        self.assertTrue({'src/hf_payload/transport/__init__.py',
                         'src/hf_payload/transport/presentation.py',
                         'tools/gui_presentation.py', 'tests/test_transport_relocation.py'} <= rows)
        builder = (ROOT / 'tools/build_single_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--paths',str(W/'src')", builder)
        self.assertIn("'--paths',str(W/'tools')", builder)
        self.assertIn("'--hidden-import','gui_presentation'", builder)
        tree = ast.parse((ROOT / 'tools/gui_install.py').read_text(encoding='utf-8'))
        self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == 'hf_payload.transport.presentation'
                            for n in ast.walk(tree)))

if __name__ == '__main__':
    unittest.main(verbosity=2)
