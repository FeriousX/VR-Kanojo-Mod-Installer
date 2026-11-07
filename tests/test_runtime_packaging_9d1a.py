"""Build-only environment isolation and fail-closed provenance checks."""
import hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from runtime_build_env import isolated_build_environment
from qualify_native_runtime import qualify
class EnvironmentTests(unittest.TestCase):
 def test_poisoned_search_paths_are_replaced(self):
  source=dict(os.environ);source.update(PATH='C:/Untrusted/libheif/bin',PYTHONHOME='C:/Untrusted/python',PYTHONPATH='C:/Untrusted/source',LD_LIBRARY_PATH='bad',PYINSTALLER_CONFIG_DIR='bad',_PYI_APPLICATION_HOME_DIR='bad')
  python=Path(sys.executable).resolve();result=isolated_build_environment(python,ROOT/'out/cache-test',source)
  windows=Path(os.environ['SystemRoot']).resolve()
  self.assertEqual(result['PATH'],os.pathsep.join(map(str,(python.parent,windows/'System32',windows))))
  for key in ('PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH','_PYI_APPLICATION_HOME_DIR'):self.assertNotIn(key,result)
  self.assertEqual(source['PATH'],'C:/Untrusted/libheif/bin')
  self.assertEqual(result['PYINSTALLER_CONFIG_DIR'],str(ROOT/'out/cache-test'))
 def test_environment_key_casing(self):
  for name in ('SystemRoot','SYSTEMROOT','systemroot'):
   result=isolated_build_environment(sys.executable,ROOT/'out/cache-test',{name:os.environ['SystemRoot'],'pAtH':'bad'})
   self.assertNotIn('bad',result['PATH']);self.assertNotIn('pAtH',result)
 def test_missing_runtime_fails(self):
  with self.assertRaises(FileNotFoundError):isolated_build_environment(ROOT/'out/missing-python.exe',ROOT/'out/cache-test')
class ProvenanceTests(unittest.TestCase):
 def setUp(self):
  (ROOT/'out').mkdir(exist_ok=True);self.temp=tempfile.TemporaryDirectory(prefix='runtime-gate-',dir=ROOT/'out');self.root=Path(self.temp.name)
  self.backend=self.root/'Backend';(self.backend/'_internal').mkdir(parents=True);self.dll=self.backend/'_internal/VCRUNTIME140.dll';self.dll.write_bytes(b'authored synthetic native placeholder, never executed')
  self.archive=self.root/'runtime.zip'
  with zipfile.ZipFile(self.archive,'w') as z:z.writestr('vcruntime140.dll',self.dll.read_bytes())
  self.evidence=self.root/'provenance.json';self.evidence.write_text(json.dumps(dict(source_sha256=hashlib.sha256(self.archive.read_bytes()).hexdigest(),native_files=[dict(path='vcruntime140.dll',sha256=hashlib.sha256(self.dll.read_bytes()).hexdigest())])))
  self.report=self.root/'report.json'
 def tearDown(self):self.temp.cleanup()
 def check(self):return qualify(self.backend,self.archive,self.evidence,self.report)
 def test_matching_case_insensitive_native_passes(self):self.assertEqual(self.check()['status'],'PASS')
 def test_unintended_dll_blocks_and_is_not_deleted(self):
  bad=self.backend/'_internal/api-ms-win-test.dll';bad.write_bytes(b'unknown')
  with self.assertRaises(ValueError):self.check()
  self.assertEqual(bad.read_bytes(),b'unknown');self.assertEqual(json.loads(self.report.read_text())['status'],'BLOCKED')
 def test_changed_native_blocks(self):
  self.dll.write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check()
 def test_missing_native_blocks(self):
  self.dll.unlink()
  with self.assertRaises(ValueError):self.check()
 def test_changed_archive_blocks(self):
  self.archive.write_bytes(b'not the approved archive')
  with self.assertRaises(ValueError):self.check()
if __name__=='__main__':unittest.main()
