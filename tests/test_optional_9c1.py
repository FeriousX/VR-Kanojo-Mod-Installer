"""Phase 9C.1: exact optional bytes through existing synthetic GUI transactions."""
import copy,hashlib,json,shutil,sys,unittest,uuid
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import gui_install as gui
from hf_payload import real_file_bridge as real
from hf_payload.component_packages import select_runtime
from hf_payload.real_components import validate_catalog,catalog_digest
from hf_payload.recovery import BASE,SyntheticArea,stable_hash,read_json
class OptionalTests(unittest.TestCase):
 def setUp(self):
  self.jobs=[];self.patch=mock.patch.multiple(gui,bridge=real,request_for=real.request_for);self.patch.start()
 def tearDown(self):
  self.patch.stop()
  for m in self.jobs:
   area=BASE/m['bridge_id'];folder=gui.folder_for(m['job'])
   assert area.is_relative_to(ROOT/'out') and folder.is_relative_to(ROOT/'out')
   shutil.rmtree(area);shutil.rmtree(folder)
 def prepare(self,mask=25,desktop='neither'):
  m=gui.prepare_job(uuid.uuid4().hex*2,mask,desktop,'demo-a');self.jobs.append(m);return m
 def test_four_independent_choices_and_exact_transaction_results(self):
  for mask in (1,9,17,25):
   with self.subTest(mask=mask):
    m=self.prepare(mask);ops=m['prepared']['operations'];paths=[r['path'] for r in ops]
    for bit,name,folder in ((8,'BepInEx.MessageCenter.dll','MessageCenter'),(16,'BepInEx.MuteInBackground.dll','MuteInBackground')):
     self.assertEqual('BepInEx/plugins/'+name in paths,bool(mask&bit))
     self.assertEqual('HF_Patch_Notices/'+folder+'/CorrespondingSource.zip' in paths,bool(mask&bit))
    result=gui.run_job(m['job'],m['plan_digest']);self.assertEqual(result['status'],'CommittedSynthetic');self.assertTrue(result['backups_verified'])
    target=Path(m['prepared']['synthetic_root']);self.assertTrue(target.is_relative_to(ROOT/'out'))
    for row in ops:self.assertEqual(stable_hash(target/row['path']),(row['after']['size'],row['after']['sha256']))
    self.assertEqual((target/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
    frame=read_json(gui.folder_for(m['job'])/'frame.json');self.assertEqual(frame['success'],'1')
    self.assertEqual('Message Center 1.1.1' in frame['display_components'],bool(mask&8))
    self.assertEqual('Mute In Background 1.1' in frame['display_components'],bool(mask&16))
 def test_both_with_desktop_and_neither(self):
  for mode in ('vrkanojo-desktop','neither'):
   m=self.prepare(desktop=mode);paths=[r['path'] for r in m['prepared']['operations']]
   self.assertEqual('BepInEx/plugins/VRKanojoDesktop.dll' in paths,mode=='vrkanojo-desktop')
 def test_source_and_license_are_exact_for_each_selection(self):
  catalog,root=real.load_catalog();validate_catalog(catalog)
  evidence=json.loads((ROOT/'third_party/Utility-r7/CLEARANCE_STATUS.json').read_text())
  for key,expected in zip(('message-center','mute'),evidence):
   rows=next(c for c in catalog['components'] if c['id']==key)['runtime_files']
   for f in rows:self.assertEqual(stable_hash(root/f['staged_source']),(f['size'],f['sha256']))
   for suffix,sha in (('.dll',expected['dll_sha256']),('/LICENSE',expected['license_sha256']),('/CorrespondingSource.zip',expected['source_archive_sha256'])):
    row=next(r for r in rows if r['destination'].endswith(suffix));self.assertEqual(row['sha256'],sha.lower())
 def test_bad_masks_and_excluded_groups(self):
  for mask in (0,2,3,4,5,7,8,16,True,-1,129):
   with self.subTest(mask=mask),self.assertRaises(ValueError):real.request_for(mask,'neither','demo-a')
  c,_=real.load_catalog()
  for key in ('runtime-editor','script-loader','resource-redirector','uncensor-loader','play-without-vr','configuration-manager'):
   with self.subTest(key=key),self.assertRaises(ValueError):select_runtime(c,['bepinex','loader-config',key],'neither')
 def test_framework_dependency_and_desktop_conflict(self):
  c,_=real.load_catalog()
  for selected,desktop,existing in [(['message-center'],'neither',()),(['bepinex','loader-config','mute'],'vrkanojo-desktop',('BepInEx/plugins/VRK_PlayWithoutVR.dll',)),(['bepinex','loader-config','play-without-vr'],'vrkanojo-desktop',())]:
   with self.assertRaises(ValueError):select_runtime(c,selected,desktop,existing)
 def test_refusal_expiry_changed_plan_and_replay(self):
  m=self.prepare()
  for token in ('','0'*64):
   with self.assertRaises(ValueError):gui.run_job(m['job'],token)
  with self.assertRaises(ValueError):gui.run_job(m['job'],m['plan_digest'],clock=lambda:m['created']+601)
  self.assertFalse((BASE/m['bridge_id']/'coordinator-intent.json').exists())
  gui.run_job(m['job'],m['plan_digest'])
  with self.assertRaises(FileExistsError):gui.run_job(m['job'],m['plan_digest'])
  changed=self.prepare(mask=9)
  with self.assertRaises(ValueError):gui.run_job(changed['job'],m['plan_digest'])
 def test_optional_hash_or_missing_source_blocks_preparation(self):
  catalog,root=real.load_catalog()
  for changed in ('hash','missing'):
   c=copy.deepcopy(catalog);f=next(c for c in c['components'] if c['id']=='mute')['runtime_files'][0]
   if changed=='hash':f['sha256']='0'*64
   else:f['staged_source']='missing/file.dll'
   with mock.patch.object(real,'load_catalog',return_value=(c,root)),self.assertRaises((ValueError,OSError)):real.prepare(real.request_for(17,'neither','demo-a'))
 def test_failure_recovers_backups_and_preserves_unknown_file(self):
  m=self.prepare()
  def fail(point,index):
   if point=='after_publish' and index==1:raise OSError('controlled optional fixture failure')
  result=gui.run_job(m['job'],m['plan_digest'],extra_fault=fail);self.assertEqual(result['status'],'Recovered')
  target=Path(m['prepared']['synthetic_root'])
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
  self.assertEqual((target/'unrelated.txt').read_bytes(),b'Unowned fixture guard: preserve.\n')
  self.assertFalse((target/'BepInEx/plugins/BepInEx.MessageCenter.dll').exists())
  self.assertEqual(real.recover(m['bridge_id'])['status'],'Recovered')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
 def test_tampered_staged_optional_payload_rejected_before_mutation(self):
  m=self.prepare(mask=17);area=BASE/m['bridge_id']
  (area/'payload/BepInEx/plugins/BepInEx.MuteInBackground.dll').write_bytes(b'changed synthetic payload')
  result=gui.run_job(m['job'],m['plan_digest'])
  self.assertEqual(result['status'],'RefusedUncertain')
  self.assertEqual(read_json(gui.folder_for(m['job'])/'frame.json')['success'],'0')
  target=Path(m['prepared']['synthetic_root'])
  self.assertFalse((target/'BepInEx/plugins/BepInEx.MuteInBackground.dll').exists())
  self.assertEqual((target/'doorstop_config.ini').read_bytes(),b'; disposable fixture seed, not a game configuration\n')
 def test_catalog_pin_and_excluded_binary_absence(self):
  c,root=real.load_catalog();review=read_json(ROOT/'manifests/real-components.review.json')
  self.assertEqual(catalog_digest(c),review['catalog_digest'])
  expected={f['staged_source'] for x in c['components'] for f in x.get('runtime_files',[])}
  actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
  self.assertEqual(actual,expected)
  self.assertEqual({x['id'] for x in c['components'] if x.get('initial_release_included')},{'bepinex','loader-config','vrkanojo-desktop','message-center','mute','fps','graphics'})
  bad=copy.deepcopy(c);bad['components'][0]['required']=not bad['components'][0]['required']
  with mock.patch.object(real,'read_json',side_effect=[bad,review]),self.assertRaises(ValueError):real.load_catalog()
 def test_native_configuration_defaults_not_installed(self):
  c,_=real.load_catalog();rows=select_runtime(c,['bepinex','loader-config','message-center','mute'],'neither')
  self.assertFalse(any(r['destination'].lower().endswith('.cfg') for r in rows if r['component'] in ('message-center','mute')))
 def test_ui_independence_and_unchanged_consent_binding(self):
  s=(ROOT/'src/installer/ui-prototype/preview.iss').read_text(encoding='utf-8')
  self.assertIn('if ComponentList.Checked[SettingsChoice] then Result := Result + 8;',s)
  self.assertIn('if ComponentList.Checked[ToolsChoice] then Result := Result + 16;',s)
  self.assertNotIn('SettingsChoice.Enabled := False;',s);self.assertNotIn('ToolsChoice.Enabled := False;',s)
  self.assertIn("'Message Center 1.1.1 (optional)'",s);self.assertIn("'Mute In Background 1.1 (optional)'",s)
  self.assertIn('DesktopOriginal.Enabled := False;',s)
  self.assertIn("IntToStr(SelectionMask()) + '|' + DesktopSelection()",s)
if __name__=='__main__':unittest.main()

