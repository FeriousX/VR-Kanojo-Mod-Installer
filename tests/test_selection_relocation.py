"""Selection CLI relocation: original imports, script behavior and frozen lookup."""
import ast
import contextlib
import hashlib
import inspect
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from hf_payload.transport import selection_cli as canonical

class SelectionRelocationTests(unittest.TestCase):
    def child(self, code, data=b'', expected=0):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code], input=data,
                                cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stderr.decode(errors='replace'))
        return json.loads(result.stdout)

    def test_main_body_unchanged_and_signature_preserved(self):
        raw = (ROOT / 'src/hf_payload/transport/selection_cli.py').read_bytes()
        body = raw.split(b'def main():', 1)[1].split(b'if __name__', 1)[0]
        self.assertEqual(hashlib.sha256(body).hexdigest(), 'ae7ab0869907a571092aa17d3d46c5898b5b46ade908ec508e04c892d560cc50')
        self.assertEqual(str(inspect.signature(canonical.main)), '()')
        self.assertNotIn('sys.path.insert', raw.decode())

    def test_legacy_module_identity_and_all_original_exports(self):
        import validate_ui_selection as legacy
        self.assertIs(legacy, canonical)
        for name in ('json', 'Path', 'sys', 'new_fixture', 'validate_selection', 'response_template', 'unique_pairs', 'main'):
            self.assertIs(getattr(legacy, name), getattr(canonical, name))

    def test_legacy_patched_globals_reach_main(self):
        import validate_ui_selection as legacy
        with mock.patch.object(legacy, 'new_fixture', side_effect=RuntimeError('sentinel fixture failure')):
            with mock.patch.object(sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(b'{}'))):
                with self.assertRaisesRegex(RuntimeError, 'sentinel fixture failure'):
                    canonical.main()

    def test_dispatcher_references_canonical_module(self):
        import portable_backend
        self.assertIs(portable_backend.validate_ui_selection, canonical)

    def test_old_then_new_and_new_then_old_source_imports(self):
        for first in ('legacy', 'canonical'):
            imports = ('import validate_ui_selection as old;import hf_payload.transport.selection_cli as new;' if first == 'legacy'
                       else 'import hf_payload.transport.selection_cli as new;import validate_ui_selection as old;')
            result = self.child('import sys,json;sys.path[:0]=' + repr([str(ROOT/'src'), str(ROOT/'tools')]) + ';' + imports +
                                'print(json.dumps(dict(same=old is new,fn=old.main is new.main)))')
            self.assertEqual(result, dict(same=True, fn=True))

    def test_src_only_canonical_and_tools_only_legacy(self):
        for path, statement in ((ROOT/'src', 'import hf_payload.transport.selection_cli as module'),
                                (ROOT/'tools', 'import validate_ui_selection as module')):
            result = self.child('import sys,json;sys.path.insert(0,' + repr(str(path)) + ');' + statement +
                                ';print(json.dumps(dict(module=module.main.__module__)))')
            self.assertEqual(result['module'], 'hf_payload.transport.selection_cli')

    def test_original_script_and_module_invalid_json_exit(self):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT/'tools/validate_ui_selection.py')],
                                input=b'{', cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2, result.stderr)
        old = json.loads(result.stdout)
        new = self.child('import sys,runpy;sys.path.insert(0,' + repr(str(ROOT/'src')) + ');'
                         'runpy.run_module("hf_payload.transport.selection_cli",run_name="__main__")', b'{', 2)
        self.assertEqual(old, new)
        self.assertFalse(new['execution_authorized'])
        self.assertEqual(new['conflicts'][0]['code'], 'INVALID_JSON')

    def test_json_failure_cases_do_not_create_fixtures(self):
        for data in (b'', b'{', b'{"a":1,"a":2}', b'NaN', b'Infinity', b' '*16385):
            with self.subTest(data=data[:30]), mock.patch.object(canonical, 'new_fixture') as create:
                with mock.patch.object(sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(data))), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(canonical.main(), 2)
                create.assert_not_called()
                self.assertEqual(json.loads(output.getvalue())['conflicts'][0]['code'], 'INVALID_JSON')

    def test_frozen_bundle_import_without_development_path(self):
        with tempfile.TemporaryDirectory(prefix='selection-import-', dir=ROOT/'out') as tmp:
            bundle = Path(tmp)/'_internal';bundle.mkdir()
            shutil.copytree(ROOT/'src/hf_payload', bundle/'hf_payload', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copyfile(ROOT/'tools/validate_ui_selection.py', bundle/'validate_ui_selection.py')
            result = self.child('import sys,json;sys.frozen=True;sys._MEIPASS=' + repr(str(bundle)) + ';'
                                'sys.path.insert(0,sys._MEIPASS);before=list(sys.path);'
                                'import validate_ui_selection as old;import hf_payload.transport.selection_cli as new;'
                                'print(json.dumps(dict(same=old is new,path_unchanged=sys.path==before,origin=new.__file__)))')
            self.assertTrue(result['same']);self.assertTrue(result['path_unchanged'])
            self.assertTrue(Path(result['origin']).is_relative_to(bundle))

    def test_one_implementation_and_static_packaging_export_edges(self):
        wrapper = ast.parse((ROOT/'tools/validate_ui_selection.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,(ast.FunctionDef,ast.ClassDef)) for n in ast.walk(wrapper)))
        from release_config import source_export_plan
        paths = {r['path'] for r in source_export_plan(ROOT)}
        self.assertTrue({'tools/validate_ui_selection.py','src/hf_payload/transport/selection_cli.py','tests/test_selection_relocation.py'} <= paths)
        source = (ROOT/'tools/build_single_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import','validate_ui_selection'",source)
        self.assertIn("'--paths',str(W/'src')",source)
        entry = ast.parse((ROOT/'tools/portable_backend.py').read_text(encoding='utf-8'))
        self.assertTrue(any(isinstance(n,ast.ImportFrom) and n.module=='hf_payload.transport' and
                            any(a.name=='selection_cli' and a.asname=='validate_ui_selection' for a in n.names) for n in ast.walk(entry)))

if __name__ == '__main__':
    unittest.main(verbosity=2)
