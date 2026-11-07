"""Release synchronization checks only: no builder/compiler/installer execution."""
import ast,csv,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from release_config import load_final_config,source_export_plan
class ReleaseSyncTests(unittest.TestCase):
 def test_final_config_and_review(self):
  c=load_final_config(ROOT);self.assertEqual(c['version'],'1.1.1');self.assertEqual(c['build_kind'],'FINAL111')
  self.assertEqual(set(c['default_off']),{'message-center','mute','fps','graphics'})
 def test_final_artifact_identity_is_truthful(self):
  a=json.loads((ROOT/'docs/RELEASE_ARTIFACTS.json').read_text());state=json.loads((ROOT/'release-status.json').read_text())
  url='https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases/tag/v1.1.0'
  self.assertIs(a['published'],True);self.assertEqual(a['status'],'PUBLISHED');self.assertEqual(a['version'],'1.1.0')
  self.assertEqual(a['release_url'],url);self.assertEqual(a['published_at'],'2026-11-07T18:10:54Z')
  self.assertIs(a['draft'],False);self.assertIs(a['prerelease'],False)
  self.assertIs(state['published'],True);self.assertEqual(state['release_url'],url);self.assertEqual(state['published_at'],a['published_at'])
  expected={'exe':('VRK-Mod-Installer-v1.1.0.exe',11133966,'0DE92037A58E3525478F33D87648FA44E028AC7B6E14E51CD71962B2943FE921'),
            'source':('VRK-Mod-Installer-v1.1.0-Source.zip',555335,'51E4CF9EEAC88739415B190EB0888973E3B3BD9035597844994B0B9786BB7BA4')}
  for kind,(name,size,sha) in expected.items():
   self.assertEqual((a[kind+'_name'],a[kind+'_bytes'],a[kind+'_sha256']),(name,size,sha))
   self.assertEqual(a[kind+'_download_url'],'https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases/download/v1.1.0/'+name)
  self.assertEqual(a['checksum_sha256'],'0C39E597641F31B9A29207A83F51A635AC3865C16185C1DF57A0A9AA3CB7FD4E')
 def test_historical_candidate_and_development_remain_distinct(self):
  a=json.loads((ROOT/'docs/V1.1.0_PACKAGE_ARTIFACTS.json').read_text());current=json.loads((ROOT/'docs/RELEASE_ARTIFACTS.json').read_text())
  self.assertIs(a['published'],False);self.assertEqual(a['status'],'VERIFIED_UNPUBLISHED_CANDIDATE');self.assertIsNone(a['release_url'])
  for key in ('exe_name','exe_bytes','exe_sha256','source_name','source_bytes','source_sha256'):self.assertEqual(a[key],current[key])
  dev=a['latest_development_reference'];self.assertEqual(dev['version'],'1.1.0-dev.3');self.assertEqual(dev['bytes'],11133715)
  self.assertEqual(dev['sha256'],'988492CB21121F2CF97B24F14189635442959C3DF464BEDD2017DF0C03689A29');self.assertNotEqual(dev['sha256'],a['exe_sha256'])
  self.assertEqual(current['latest_development_reference'],dev)
 def test_historical_v100_and_recipe_are_not_current_publication(self):
  a=json.loads((ROOT/'docs/history/v1.0.0/RELEASE_ARTIFACTS.json').read_text())
  self.assertEqual(a['version'],'1.0.0');self.assertIs(a['published'],True);self.assertFalse(a['prerelease'])
  self.assertEqual(a['exe_sha256'],'4ECD964F3F9CCFC4DF5184E497223488B0F477AD764FC34E790B4FD6B127826F')
  self.assertEqual(a['source_sha256'],'F0A6AF8EF59C892F6E51182B176F5DA64F7F3048D88814812607EE707CD3599C')
  self.assertIs(load_final_config(ROOT,'1.1.0')['published'],False) # Immutable build-time recipe, not current release status.
 def test_owner_evidence_separate(self):
  s=json.loads((ROOT/'release-status.json').read_text());self.assertIn('OWNER_REPORTED',s['owner_reported_testing']['core_installation_and_gameplay'])
  for k in ('recovery_retest','additional_dpi','clean_windows'):self.assertEqual(s['owner_reported_testing'][k],'NOT_VERIFIED')
  self.assertFalse(any(s['independent_verification'].values()));self.assertFalse(s['release_qualified'])
 def test_real_reference_inventory(self):
  a=json.loads((ROOT/'docs/EMBEDDED_FILE_INVENTORY.json').read_text());self.assertEqual(a['resource_count'],len(a['resources']));self.assertEqual(a['component_files'],56)
  self.assertEqual(a['native_files'],18)
  if 'REFERENCE' in a['status']:self.assertIsNone(a['final_resource_count'])
  else:self.assertEqual(a['final_resource_count'],len(a['resources']));self.assertEqual(a['status'],'FINAL_BUILD_INPUTS_VERIFIED')
 def test_license_tables_agree(self):
  a=list(csv.DictReader(io.StringIO((ROOT/'docs/license-audit.csv').read_text())));b=json.loads((ROOT/'docs/license-audit.json').read_text());self.assertEqual(a,b)
  expected={'Message Center':('1.1.1','GPL-3.0'),'Mute In Background':('1.1','GPL-3.0'),'FPS Counter':('3.1','Apache-2.0 AND zlib'),'Graphics Settings (official)':('1.2.1','GPL-3.0')}
  for name,(version,license) in expected.items():
   r=next(x for x in a if x['component']==name);self.assertEqual((r['version'],r['license'],r['status']),(version,license,'CLEARED'))
 def test_recovery_no_universal_bundle(self):
  t=(ROOT/'docs/RECOVERY.md').read_text();self.assertNotIn('81896c44bd1ee122',t);self.assertNotIn('95a892e2fcb0edda',t)
  self.assertIn('<matching-transaction-bundle>',t);self.assertIn('same Windows account',t)
 def test_inno_macro_defaults(self):
  s=(ROOT/'src/installer/ui-prototype/preview.iss').read_text();self.assertIn('#define ReleaseVersion "1.1.1"',s);self.assertIn('#define ReleaseNumericVersion "1.1.1.0"',s)
  self.assertIn('AppVersion={#ReleaseVersion}',s);self.assertIn('PrivilegesRequired=lowest',s)
 def test_wrapper_defines_are_real_lines(self):
  tree=ast.parse((ROOT/'tools/build_single_exe.py').read_text())
  expr=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='release_defs' for t in n.targets))
  result=eval(compile(ast.Expression(expr),'<release constants>','eval'),{'chr':chr,'kind':'FINAL110'})
  self.assertEqual(result,'#define ReleaseVersion "1.1.0"\n#define ReleaseNumericVersion "1.1.0.0"\n')
  result=eval(compile(ast.Expression(expr),'<release constants>','eval'),{'chr':chr,'kind':'FINAL111'})
  self.assertEqual(result,'#define ReleaseVersion "1.1.1"\n#define ReleaseNumericVersion "1.1.1.0"\n')
 def test_final_builder_native_gate(self):
  s=(ROOT/'tools/build_single_exe.py').read_text();self.assertIn("if kind in ('DEV110','FINAL110','FINAL111'):",s)
  self.assertIn("final_config['runtime_archive_sha256']",s);self.assertIn("final_config['runtime_provenance_sha256']",s)
 def test_compiler_target_is_separate(self):
  s=(ROOT/'tools/compile_single_exe.ps1').read_text();self.assertIn('out\\FinalRelease_v1.1.0',s);self.assertIn('Refusing artifact overwrite',s);self.assertIn('requires explicit qualified -CompilerPath',s);self.assertIn('out\\FinalRelease_v1.1.1',s);self.assertIn("$Kind='FINAL111'",s)
 def test_export_current_source_only(self):
  rows=source_export_plan(ROOT);self.assertTrue(rows);names={x['path'] for x in rows}
  self.assertTrue({'CONTRIBUTING.md','docs/ARCHITECTURE.md','docs/README.md','docs/TESTING.md'} <= names);self.assertIn('LICENSE',names);self.assertIn('tools/build_single_exe.py',names);self.assertIn('manifests/source-export-rules.json',names)
  self.assertFalse(any(n.lower().endswith(('.dll','.exe','.pyd','.log')) for n in names))
  self.assertFalse(any(n.split('/')[0] in ('out','build','cache','payload') for n in names))
 def test_export_detects_changed_input(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'out') as temp:
   r=Path(temp);(r/'manifests').mkdir();(r/'README.md').write_text('changed')
   policy={'schema_version':1,'mode':'explicit-source-only','approved_source_archive_sha256':[],'files':[{'path':'README.md','sha256':'0'*64}]}
   (r/'manifests/source-export-rules.json').write_text(json.dumps(policy))
   with self.assertRaises(ValueError):source_export_plan(r)
 def test_export_rejects_binary_private_traversal(self):
  for name in ('../escape','C:/escape','out/private.json','backups/private.json','src/plugin.dll','arbitrary.md'):
   with self.subTest(path=name),tempfile.TemporaryDirectory(dir=ROOT/'out') as temp:
    r=Path(temp);(r/'manifests').mkdir();(r/'src').mkdir()
    policy={'schema_version':1,'mode':'explicit-source-only','approved_source_archive_sha256':[],'files':[{'path':name,'sha256':'0'*64}]}
    (r/'manifests/source-export-rules.json').write_text(json.dumps(policy))
    with self.assertRaises((ValueError,OSError)):source_export_plan(r)
 def test_source_pyproject_version(self):
  import tomllib
  v=tomllib.loads((ROOT/'pyproject.toml').read_text());self.assertEqual(v['project']['version'],'1.1.1');self.assertFalse(v['tool']['vrk-mod-installer']['release-qualified'])
 def test_final111_and_historical_recipe_guards(self):
  self.assertEqual(load_final_config(ROOT)['distribution_dir'],'out/FinalRelease_v1.1.1')
  self.assertEqual(load_final_config(ROOT,'1.1.0')['distribution_dir'],'out/FinalRelease_v1.1.0')
  for version in ('../escape','1.1.2',True):
   with self.subTest(version=version),self.assertRaises(ValueError):load_final_config(ROOT,version)
  with tempfile.TemporaryDirectory(dir=ROOT/'out') as temp:
   root=Path(temp);(root/'manifests').mkdir()
   cfg=json.loads((ROOT/'manifests/final-v1.1.1.json').read_text());cfg['distribution_dir']='out/FinalRelease_v1.1.0'
   (root/'manifests/final-v1.1.1.json').write_text(json.dumps(cfg))
   with self.assertRaises(ValueError):load_final_config(root)
  import package_source110,inspect
  self.assertEqual(inspect.signature(package_source110.package).parameters['version'].default,'1.1.1')
 def test_next_release_and_owner_evidence(self):
  p=json.loads((ROOT/'docs/RELEASE_PREPARATION.json').read_text())
  self.assertEqual(p['version'],'1.1.1');self.assertIs(p['published'],False);self.assertIs(p['artifact_built'],False)
  self.assertIsNone(p['exe_sha256']);self.assertIsNone(p['source_sha256'])
  t=p['tested_reference'];self.assertEqual(t['sha256'],'9409B0299E0F75A7A9952B456A47ED0B8BE0C8ACD2A53E92F9613ACEF86F0620')
  self.assertEqual(t['bytes'],11135199);self.assertEqual(t['owner_installation_and_gameplay'],'PASS_OWNER_REPORTED')
  for name in ('recovery_retest','additional_dpi','stock_windows'):self.assertEqual(p['qualification'][name],'NOT_VERIFIED')

if __name__=='__main__':unittest.main()
