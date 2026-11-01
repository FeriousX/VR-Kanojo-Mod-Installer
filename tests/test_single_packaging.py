import sys,types,unittest
from pathlib import Path
from unittest import mock
from hf_payload import runtime_paths as r
class PersistentPathTests(unittest.TestCase):
 def test_executable_move_does_not_move_state(self):
  profile=types.SimpleNamespace(STATE_PARTS=('FeriousX','VRKMI','state'))
  with mock.patch.dict(sys.modules,backend_profile=profile),mock.patch.object(sys,'frozen',True,create=True),mock.patch.object(r,'user_local_appdata',return_value=Path('C:/Users/Test/AppData/Local')):
   with mock.patch.object(sys,'executable','C:/deep folder/setup.exe'):first=r.workspace()
   with mock.patch.object(sys,'executable','C:/elsewhere/recovery.exe'):second=r.workspace()
   self.assertEqual(first,second);self.assertEqual(first,Path('C:/Users/Test/AppData/Local/FeriousX/VRKMI/state'))
 def test_bad_compiled_scope_rejected(self):
  for parts in [('..','state'),('C:/outside',),('bad\\part',)]:
   with mock.patch.dict(sys.modules,backend_profile=types.SimpleNamespace(STATE_PARTS=parts)),mock.patch.object(sys,'frozen',True,create=True):
    with self.assertRaises(ValueError):r.workspace()
 def test_legacy_portable_state_still_supported(self):
  with mock.patch.object(r,'persistent_profile',return_value=None),mock.patch.object(sys,'frozen',True,create=True),mock.patch.object(sys,'executable','C:/Old/Backend/HFBackend.exe'):
   self.assertEqual(r.workspace(),Path('C:/Old/Backend/state'))
 def test_source_does_not_use_extraction_state(self):
  with mock.patch.object(sys,'frozen',False,create=True):self.assertEqual(r.workspace(),Path(__file__).resolve().parents[1])
