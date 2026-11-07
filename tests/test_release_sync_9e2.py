"""Release synchronization checks only: no builder/compiler/installer execution."""
import ast,csv,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from release_config import load_final_config,source_export_plan
class ReleaseSyncTests(unittest.TestCase):
 def test_final_config_and_review(self):
  c=load_final_config(ROOT);self.assertEqual(c['version'],'1.1.0');self.assertEqual(c['build_kind'],'FINAL110')
  self.assertEqual(set(c['default_off']),{'message-center','mute','fps','graphics'})
 def test_final_artifact_identity_is_truthful(self):
  a=json.loads((ROOT/'docs/RELEASE_ARTIFACTS.json').read_text());self.assertFalse(a['published'])
  if a['status']=='PREPARED_NOT_BUILT':
   for k in ('exe_sha256','source_sha256','exe_bytes','source_bytes'):self.assertIsNone(a[k])
  else:
   self.assertEqual(a['status'],'BUILT_UNPUBLISHED_CANDIDATE');self.assertRegex(a['exe_sha256'],r'^[A-F0-9]{64}$');self.assertGreater(a['exe_bytes'],0)
   self.assertIsNone(a['source_sha256']);self.assertEqual(a['source_hash_record'],'EXTERNAL_RELEASE_ARTIFACTS')
  self.assertEqual(a['latest_development_reference']['version'],'1.1.0-dev.3')
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
  s=(ROOT/'src/installer/ui-prototype/preview.iss').read_text();self.assertIn('#define ReleaseVersion "1.1.0"',s);self.assertIn('#define ReleaseNumericVersion "1.1.0.0"',s)
  self.assertIn('AppVersion={#ReleaseVersion}',s);self.assertIn('PrivilegesRequired=lowest',s)
 def test_wrapper_defines_are_real_lines(self):
  tree=ast.parse((ROOT/'tools/build_single_exe.py').read_text())
  expr=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='release_defs' for t in n.targets))
  result=eval(compile(ast.Expression(expr),'<release constants>','eval'),{'chr':chr,'kind':'FINAL110'})
  self.assertEqual(result,'#define ReleaseVersion "1.1.0"\n#define ReleaseNumericVersion "1.1.0.0"\n')
 def test_final_builder_native_gate(self):
  s=(ROOT/'tools/build_single_exe.py').read_text();self.assertIn("if kind in ('DEV110','FINAL110'):",s)
  self.assertIn("final_config['runtime_archive_sha256']",s);self.assertIn("final_config['runtime_provenance_sha256']",s)
 def test_compiler_target_is_separate(self):
  s=(ROOT/'tools/compile_single_exe.ps1').read_text();self.assertIn('out\\FinalRelease_v1.1.0',s);self.assertIn('Refusing artifact overwrite',s);self.assertIn('FINAL110 requires explicit',s)
 def test_export_current_source_only(self):
  rows=source_export_plan(ROOT);self.assertTrue(rows);names={x['path'] for x in rows}
  self.assertIn('LICENSE',names);self.assertIn('tools/build_single_exe.py',names);self.assertIn('manifests/source-export-rules.json',names)
  self.assertFalse(any(n.lower().endswith(('.dll','.exe','.pyd','.log')) for n in names))
  self.assertFalse(any(n.split('/')[0] in ('out','build','cache','payload') for n in names))
 def test_export_detects_changed_input(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'out') as temp:
   r=Path(temp);(r/'manifests').mkdir();(r/'README.md').write_text('changed')
   policy={'schema_version':1,'mode':'explicit-source-only','approved_source_archive_sha256':[],'files':[{'path':'README.md','sha256':'0'*64}]}
   (r/'manifests/source-export-rules.json').write_text(json.dumps(policy))
   with self.assertRaises(ValueError):source_export_plan(r)
 def test_export_rejects_binary_private_traversal(self):
  for name in ('../escape','C:/escape','out/private.json','backups/private.json','src/plugin.dll'):
   with self.subTest(path=name),tempfile.TemporaryDirectory(dir=ROOT/'out') as temp:
    r=Path(temp);(r/'manifests').mkdir();(r/'src').mkdir()
    policy={'schema_version':1,'mode':'explicit-source-only','approved_source_archive_sha256':[],'files':[{'path':name,'sha256':'0'*64}]}
    (r/'manifests/source-export-rules.json').write_text(json.dumps(policy))
    with self.assertRaises((ValueError,OSError)):source_export_plan(r)
 def test_source_pyproject_version(self):
  import tomllib
  v=tomllib.loads((ROOT/'pyproject.toml').read_text());self.assertEqual(v['project']['version'],'1.1.0');self.assertFalse(v['tool']['vrk-mod-installer']['release-qualified'])
if __name__=='__main__':unittest.main()
