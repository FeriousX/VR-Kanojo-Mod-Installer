"""Graphics Settings 1.2.1 integration: synthetic files only, no plugin execution."""
import hashlib,json,sys,unittest,copy
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import test_optional_9c1 as prior
import gui_install as gui
from hf_payload import real_file_bridge as real
from hf_payload.component_packages import select_runtime
from hf_payload.recovery import BASE,stable_hash,read_json
class GraphicsTests(unittest.TestCase):
 setUp=prior.OptionalTests.setUp
 tearDown=prior.OptionalTests.tearDown
 prepare=prior.OptionalTests.prepare
 def test_all_sixteen_independent_plans(self):
  for optional in range(0,128,8):
   with self.subTest(mask=1|optional):
    m=self.prepare(mask=1|optional);paths={x['path'] for x in m['prepared']['operations']}
    for bit,name in ((8,'BepInEx.MessageCenter.dll'),(16,'BepInEx.MuteInBackground.dll'),(32,'FPSCounter.dll'),(64,'GraphicsSettings.dll')):
     self.assertEqual('BepInEx/plugins/'+name in paths,bool(optional&bit))
    frame=read_json(gui.folder_for(m['job'])/'frame.json')
    self.assertEqual('Graphics Settings 1.2.1' in frame['display_components'],bool(optional&64))
    self.assertFalse((BASE/m['bridge_id']/'coordinator-intent.json').exists())
 def test_graphics_alone_and_all_with_desktop_commit_exact_files(self):
  for mask,mode in ((65,'neither'),(121,'vrkanojo-desktop')):
   with self.subTest(mask=mask,desktop=mode):
    m=self.prepare(mask=mask,desktop=mode);result=gui.run_job(m['job'],m['plan_digest'])
    self.assertEqual(result['status'],'CommittedSynthetic');self.assertTrue(result['backups_verified'])
    root=Path(m['prepared']['synthetic_root']);self.assertTrue(root.is_relative_to(ROOT/'out'))
    for row in m['prepared']['operations']:self.assertEqual(stable_hash(root/row['path']),(row['after']['size'],row['after']['sha256']))
    self.assertEqual((root/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
    self.assertEqual(real.recover(m['bridge_id'])['status'],'CommittedSynthetic')
 def test_exact_official_dll_and_licenses_source(self):
  c,source=real.load_catalog();g=next(x for x in c['components'] if x['id']=='graphics')
  self.assertEqual(g['dependencies'],['bepinex']);self.assertFalse(g['required'])
  dll=next(x for x in g['runtime_files'] if x['destination'].endswith('.dll'))
  self.assertEqual(dll['sha256'],'e6149270785b1f1c152a1a3fcb39b4d2e71c69a968d2ccfff89a20b1d10c23a2')
  self.assertNotEqual(dll['sha256'],'538225163e1609ca72a0b77ef21c1ed4414df46aaf21ea40c698eaff87430502')
  for f in g['runtime_files']:self.assertEqual(stable_hash(source/f['staged_source']),(f['size'],f['sha256']))
  import zipfile
  src=next(f for f in g['runtime_files'] if f['destination'].endswith('/CorrespondingSource.zip'))
  with zipfile.ZipFile(source/src['staged_source']) as z:
   self.assertFalse(any(n.lower().endswith(('.dll','.exe')) for n in z.namelist()))
   self.assertTrue(any(n.endswith('GraphicsSettings.csproj') for n in z.namelist()))
  names={Path(f['destination']).name for f in g['runtime_files']}
  self.assertTrue({'GraphicsSettings-GPL-3.0.txt','SOURCE_INFORMATION.md','ATTRIBUTION_AND_USAGE.md','CorrespondingSource.zip'}<=names)
 def test_missing_or_changed_graphics_and_license_rejected(self):
  c,source=real.load_catalog()
  for changed in ('dll','license','missing'):
   bad=copy.deepcopy(c);files=next(x for x in bad['components'] if x['id']=='graphics')['runtime_files']
   f=next(x for x in files if x['destination'].endswith('GraphicsSettings-GPL-3.0.txt')) if changed=='license' else files[0]
   if changed=='missing':f['staged_source']='missing/GraphicsSettings.dll'
   else:f['sha256']='0'*64
   with mock.patch.object(real,'load_catalog',return_value=(bad,source)),self.assertRaises((ValueError,OSError)):real.prepare(real.request_for(65,'neither','demo-a'))
 def test_tampered_prepared_graphics_refused_without_target_changes(self):
  m=self.prepare(mask=65);area=BASE/m['bridge_id'];(area/'payload/BepInEx/plugins/GraphicsSettings.dll').write_bytes(b'bad bytes')
  result=gui.run_job(m['job'],m['plan_digest']);self.assertEqual(result['status'],'RefusedUncertain')
  target=Path(m['prepared']['synthetic_root']);self.assertFalse((target/'BepInEx/plugins/GraphicsSettings.dll').exists())
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
 def test_consent_refusal_changed_selection_and_replay(self):
  a=self.prepare(mask=65);b=self.prepare(mask=1)
  for token in ('','0'*64,b['plan_digest']):
   with self.assertRaises(ValueError):gui.run_job(a['job'],token)
  self.assertFalse((BASE/a['bridge_id']/'coordinator-intent.json').exists())
  with self.assertRaises(ValueError):gui.run_job(a['job'],a['plan_digest'],clock=lambda:a['created']+601)
  gui.run_job(a['job'],a['plan_digest'])
  with self.assertRaises(FileExistsError):gui.run_job(a['job'],a['plan_digest'])
 def test_failure_after_graphics_publication_rolls_back(self):
  m=self.prepare(mask=121);target=Path(m['prepared']['synthetic_root']);triggered=[]
  def fail(point,index):
   if point=='after_publish' and (target/'BepInEx/plugins/GraphicsSettings.dll').exists():triggered.append(True);raise OSError('synthetic failure after FPS publication')
  result=gui.run_job(m['job'],m['plan_digest'],extra_fault=fail);self.assertTrue(triggered);self.assertEqual(result['status'],'Recovered')
  self.assertFalse((target/'BepInEx/plugins/GraphicsSettings.dll').exists())
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
  self.assertEqual((target/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
  self.assertEqual(real.recover(m['bridge_id'])['status'],'Recovered')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
 def test_framework_harmony_and_remaining_exclusions(self):
  c,_=real.load_catalog()
  with self.assertRaises(ValueError):select_runtime(c,['graphics'],'neither')
  rows=select_runtime(c,['bepinex','loader-config','graphics'],'neither');names={r['destination'] for r in rows}
  self.assertIn('BepInEx/core/0Harmony.dll',names);self.assertIn('BepInEx/core/0Harmony20.dll',names)
  for key in ('runtime-editor','script-loader','resource-redirector','uncensor-loader','play-without-vr','configuration-manager'):
   with self.subTest(key=key),self.assertRaises(ValueError):select_runtime(c,['bepinex','loader-config',key],'neither')
  for mask in (0,2,3,7,32,129,True):
   with self.assertRaises(ValueError):real.request_for(mask,'neither','demo-a')
 def test_ui_checkbox_default_and_shared_backend_mapping(self):
  s=(ROOT/'src/installer/ui-prototype/preview.iss').read_text(encoding='utf-8')
  self.assertIn("GraphicsChoice := AddComponentChoice('Graphics Settings 1.2.1 (optional)'",s)
  self.assertIn("'Startup values via config file; no advanced configuration menu.', False, True);",s)
  self.assertIn('if ComponentList.Checked[GraphicsChoice] then Result := Result + 64;',s)
  self.assertIn('ValidatedBinding = SelectionBinding()',s)
  for name in ('real_file_bridge.py','private_game_bridge.py'):
   self.assertIn("if request['mask']&64:selected+=['graphics']",(ROOT/'src/hf_payload'/name).read_text())
 def test_native_configuration_preserved(self):
  m=self.prepare(mask=65);target=Path(m['prepared']['synthetic_root'])
  config=target/'BepInEx/config/keelhauled.graphicssettings.cfg';config.parent.mkdir(parents=True,exist_ok=True)
  config.write_bytes(b'User-owned graphics configuration: preserve exactly.\n')
  result=gui.run_job(m['job'],m['plan_digest'])
  self.assertEqual(result['status'],'CommittedSynthetic')
  self.assertEqual(config.read_bytes(),b'User-owned graphics configuration: preserve exactly.\n')
 def test_unknown_existing_graphics_file_not_overwritten(self):
  m=self.prepare(mask=65);target=Path(m['prepared']['synthetic_root']);dll=target/'BepInEx/plugins/GraphicsSettings.dll'
  dll.write_bytes(b'Unknown user plugin added after planning')
  result=gui.run_job(m['job'],m['plan_digest'])
  self.assertNotEqual(result['status'],'CommittedSynthetic')
  self.assertEqual(dll.read_bytes(),b'Unknown user plugin added after planning')
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
if __name__=='__main__':unittest.main()

