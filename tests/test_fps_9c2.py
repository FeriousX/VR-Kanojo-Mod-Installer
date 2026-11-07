"""FPS Counter 3.1 integration: synthetic files only, no plugin execution."""
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
class FPSTests(unittest.TestCase):
 setUp=prior.OptionalTests.setUp
 tearDown=prior.OptionalTests.tearDown
 prepare=prior.OptionalTests.prepare
 def test_all_eight_independent_plans(self):
  for optional in (0,8,16,24,32,40,48,56):
   with self.subTest(mask=1|optional):
    m=self.prepare(mask=1|optional);paths={x['path'] for x in m['prepared']['operations']}
    for bit,name in ((8,'BepInEx.MessageCenter.dll'),(16,'BepInEx.MuteInBackground.dll'),(32,'FPSCounter.dll')):
     self.assertEqual('BepInEx/plugins/'+name in paths,bool(optional&bit))
    frame=read_json(gui.folder_for(m['job'])/'frame.json')
    self.assertEqual('FPS Counter 3.1' in frame['display_components'],bool(optional&32))
    self.assertEqual('enable its native configuration after installation' in frame['display_components'],bool(optional&16))
    self.assertFalse((BASE/m['bridge_id']/'coordinator-intent.json').exists())
 def test_fps_alone_and_all_with_desktop_commit_exact_files(self):
  for mask,mode in ((33,'neither'),(57,'vrkanojo-desktop')):
   with self.subTest(mask=mask,desktop=mode):
    m=self.prepare(mask=mask,desktop=mode);result=gui.run_job(m['job'],m['plan_digest'])
    self.assertEqual(result['status'],'CommittedSynthetic');self.assertTrue(result['backups_verified'])
    root=Path(m['prepared']['synthetic_root']);self.assertTrue(root.is_relative_to(ROOT/'out'))
    for row in m['prepared']['operations']:self.assertEqual(stable_hash(root/row['path']),(row['after']['size'],row['after']['sha256']))
    self.assertEqual((root/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
    self.assertEqual(real.recover(m['bridge_id'])['status'],'CommittedSynthetic')
 def test_exact_official_dll_and_all_licenses_source(self):
  c,source=real.load_catalog();fps=next(x for x in c['components'] if x['id']=='fps');self.assertEqual(fps['dependencies'],['bepinex']);self.assertFalse(fps['required'])
  ev=read_json(ROOT/'third_party/FPSCounter-v3.1/CLEARANCE_STATUS.json')
  dll=next(x for x in fps['runtime_files'] if x['destination'].endswith('.dll'))
  self.assertEqual(dll['sha256'],ev['archive']['members'][0]['sha256'].lower())
  self.assertNotEqual(dll['sha256'],ev['not_cleared_by_this_review']['original_hf_dll_sha256'])
  self.assertEqual(dll['sha256'],'333c467be5d3edc845a9a97d0d0a2c2269e796c63cf0ab6ff72d1ba74323a982')
  for f in fps['runtime_files']:
   self.assertEqual(stable_hash(source/f['staged_source']),(f['size'],f['sha256']))
   if f['destination'].endswith('.txt') or f['destination'].endswith('.md'):
    self.assertEqual((source/f['staged_source']).read_bytes(),(ROOT/'third_party/FPSCounter-v3.1/notices'/Path(f['destination']).name).read_bytes())
  names={Path(f['destination']).name for f in fps['runtime_files']}
  for name in ('Apache-2.0.txt','Gavin-Pugh-Original-Source-Notices.txt','Zlib-License-Reference.txt','Original-Assembly-Notices.txt','CorrespondingSource.zip'):self.assertIn(name,names)
  src=next(f for f in fps['runtime_files'] if f['destination'].endswith('/CorrespondingSource.zip'));self.assertEqual(src['sha256'],ev['source']['sha256'].lower())
 def test_missing_or_changed_fps_and_license_rejected(self):
  c,source=real.load_catalog()
  for changed in ('dll','license','missing'):
   bad=copy.deepcopy(c);files=next(x for x in bad['components'] if x['id']=='fps')['runtime_files']
   f=next(x for x in files if x['destination'].endswith('Apache-2.0.txt')) if changed=='license' else files[0]
   if changed=='missing':f['staged_source']='missing/FPSCounter.dll'
   else:f['sha256']='0'*64
   with mock.patch.object(real,'load_catalog',return_value=(bad,source)),self.assertRaises((ValueError,OSError)):real.prepare(real.request_for(33,'neither','demo-a'))
 def test_tampered_prepared_fps_refused_without_target_changes(self):
  m=self.prepare(mask=33);area=BASE/m['bridge_id'];(area/'payload/BepInEx/plugins/FPSCounter.dll').write_bytes(b'bad bytes')
  result=gui.run_job(m['job'],m['plan_digest']);self.assertEqual(result['status'],'RefusedUncertain')
  target=Path(m['prepared']['synthetic_root']);self.assertFalse((target/'BepInEx/plugins/FPSCounter.dll').exists())
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
 def test_consent_refusal_changed_selection_and_replay(self):
  a=self.prepare(mask=33);b=self.prepare(mask=1)
  for token in ('','0'*64,b['plan_digest']):
   with self.assertRaises(ValueError):gui.run_job(a['job'],token)
  self.assertFalse((BASE/a['bridge_id']/'coordinator-intent.json').exists())
  with self.assertRaises(ValueError):gui.run_job(a['job'],a['plan_digest'],clock=lambda:a['created']+601)
  gui.run_job(a['job'],a['plan_digest'])
  with self.assertRaises(FileExistsError):gui.run_job(a['job'],a['plan_digest'])
 def test_failure_after_fps_publication_rolls_back(self):
  m=self.prepare(mask=57);target=Path(m['prepared']['synthetic_root']);triggered=[]
  def fail(point,index):
   if point=='after_publish' and (target/'BepInEx/plugins/FPSCounter.dll').exists():triggered.append(True);raise OSError('synthetic failure after FPS publication')
  result=gui.run_job(m['job'],m['plan_digest'],extra_fault=fail);self.assertTrue(triggered);self.assertEqual(result['status'],'Recovered')
  self.assertFalse((target/'BepInEx/plugins/FPSCounter.dll').exists())
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
  self.assertEqual((target/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
  self.assertEqual(real.recover(m['bridge_id'])['status'],'Recovered')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
 def test_framework_harmony_and_remaining_exclusions(self):
  c,_=real.load_catalog()
  with self.assertRaises(ValueError):select_runtime(c,['fps'],'neither')
  rows=select_runtime(c,['bepinex','loader-config','fps'],'neither');names={r['destination'] for r in rows}
  self.assertIn('BepInEx/core/0Harmony.dll',names);self.assertIn('BepInEx/core/0Harmony20.dll',names)
  for key in ('runtime-editor','script-loader','resource-redirector','uncensor-loader','play-without-vr','configuration-manager'):
   with self.subTest(key=key),self.assertRaises(ValueError):select_runtime(c,['bepinex','loader-config',key],'neither')
  for mask in (0,2,3,7,32,129,True):
   with self.assertRaises(ValueError):real.request_for(mask,'neither','demo-a')
 def test_ui_checkbox_default_and_shared_backend_mapping(self):
  s=(ROOT/'src/installer/ui-prototype/preview.iss').read_text(encoding='utf-8')
  self.assertIn("FPSChoice := AddComponentChoice('FPS Counter 3.1 (optional)'",s)
  self.assertIn("'Displays frame-rate statistics; official reviewed v3.1 plugin.', False, True);",s)
  self.assertIn('if ComponentList.Checked[FPSChoice] then Result := Result + 32;',s)
  self.assertIn('Enable its native configuration after installation',s)
  self.assertIn('ValidatedBinding = SelectionBinding()',s)
  for name in ('real_file_bridge.py','private_game_bridge.py'):
   self.assertIn("if request['mask']&32:selected+=['fps']",(ROOT/'src/hf_payload'/name).read_text())
if __name__=='__main__':unittest.main()
