"""Build qualified single-EXE installation resources using the qualified existing tools."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'src'))
from hf_payload.recovery import digest
from hf_payload.validator import stable_hash
from hf_payload.real_components import validate_catalog
p=argparse.ArgumentParser();p.add_argument('--qualification',action='store_true');p.add_argument('--milestone',choices=('B81','B82','RC83','RC1'),default='RC1');p.add_argument('--python',required=True,help='Explicit qualified Python executable');a=p.parse_args()
kind='Q8' if a.qualification else a.milestone;OUT=W/'out'/kind;REPORT=W/'out'/('public-rc1' if kind=='RC1' else ('phase8c3' if kind=='RC83' else ('phase8b2' if kind=='B82' else 'phase8b1')));BUILD=W/'build'/kind
OUT.mkdir(exist_ok=False);REPORT.mkdir(exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
policy=dict(schema=1,scope='compatible-original-game-v1',protected_roots=[],game_version=None);scope='FeriousX\\VRKMI'
if a.qualification:
 # Authored fake PE/managed bytes, no real game access or execution.
 import uuid,struct
 from hf_payload.external_root import FIXTURE_ROOT,qualify_private_copy
 FIXTURE_ROOT.mkdir(exist_ok=True);root=FIXTURE_ROOT/str(uuid.uuid4());(root/'VRKanojo_Data/Managed').mkdir(parents=True)
 pe=bytearray(100);pe[:2]=b'MZ';struct.pack_into('<I',pe,60,64);pe[64:70]=b'PE\0\0\x64\x86'
 files={'VRKanojo.exe':pe,'VRKanojo_Data/app.info':b'ILLUSION_VRkanojo\nVRKanojo','VRKanojo_Data/globalgamemanagers':b'5.4.5p1\0fixture',
        'VRKanojo_Data/Managed/Assembly-CSharp.dll':b'fake game','VRKanojo_Data/Managed/UnityEngine.dll':b'fake engine','VRKanojo_Data/Managed/UnityEngine.UI.dll':b'fake UI'}
 for name,data in files.items():(root/name).write_bytes(data)
 profile=qualify_private_copy(str(root),selected_manually=True,disposable_confirmed=True,protected_roots=[])
 policy=dict(schema=1,scope='private-disposable-game-test',target=str(root),target_id=profile['root_id'],layout=profile['layout'],files=profile['files'],dependencies=[],protected_roots=[],game_version=None)
 scope+='\\q8a'+root.name[:6]
 (REPORT/'qualification-target.json').write_text(json.dumps(dict(root=str(root),policy=policy,scope=scope),indent=2))
parts=tuple(scope.split('\\'))+('state',)
(BUILD/'backend_profile.py').write_text('STATE_PARTS = '+repr(parts)+'\n')
catalog=json.loads((W/'manifests/real-components.json').read_text());validate_catalog(catalog)
assert digest(catalog)==json.loads((W/'manifests/real-components.review.json').read_text())['catalog_digest']
(BUILD/'real_payload_pin.py').write_text('CATALOG_DIGEST = '+repr(digest(catalog))+'\n')
(BUILD/'private_target_pin.py').write_text('POLICY_DIGEST = '+repr(digest(policy))+'\n')
entry=W/'tools'/('qualification_backend8a.py' if a.qualification else 'portable_backend.py')
cmd=[str(Path(a.python).resolve(strict=True)),'-I','-m','PyInstaller','--onedir','--console','--noupx','--name','HFBackend','--paths',str(BUILD),'--paths',str(W/'src'),'--paths',str(W/'tools'),'--exclude-module','tkinter','--exclude-module','unittest','--exclude-module','pip','--exclude-module','setuptools','--distpath',str(OUT),'--workpath',str(BUILD),'--specpath',str(BUILD),str(entry)]
with (REPORT/(kind+'-backend-build.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=W)
backend=OUT/'Backend';(OUT/'HFBackend').rename(backend);(backend/'PrivateTarget.json').write_text(json.dumps(policy))
components=backend/'Components';components.mkdir();(components/'catalog.json').write_text(json.dumps(catalog))
for c in catalog['components']:
 if c.get('initial_release_included'):
  for f in c['runtime_files']:
   source=W/'payload'/f['staged_source'];assert stable_hash(source)==(f['size'],f['sha256'])
   target=components/f['staged_source'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
shutil.copytree(W/'out/Portable Backend/HFBackend/Notices',backend/'Notices');shutil.copytree(W/'payload/component-review/_notices_reference',backend/'Notices/ComponentReference')
specs=[dict(path=p.relative_to(OUT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(backend.rglob('*')) if p.is_file()]
manifest=dict(schema=1,files=specs);raw=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode();(OUT/'Resources.json').write_bytes(raw)
helper=r'''param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$Job)
$ErrorActionPreference='Stop'
# Use stock Windows modules explicitly; no inherited PSModulePath/Python dependency.
Import-Module ($PSHOME+'\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
Import-Module ($PSHOME+'\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1') -ErrorAction Stop
$root=$PSScriptRoot
function AssertNoLink([string]$Path){
 $item=Get-Item -LiteralPath $Path -Force
 while($null -ne $item){
  if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked recovery resource or ancestor refused'}
  if($item.PSIsContainer){$item=$item.Parent}else{$item=$item.Directory}
 }
}
AssertNoLink $root
$manifest=Join-Path $root 'Resources.json'
if((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash -ne '__MANIFEST__'){throw 'Recovery resource manifest changed; keep state and restore a verified runtime.'}
$m=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
foreach($entry in $m.files){
 $path=Join-Path $root $entry.path
 AssertNoLink $path
 $item=Get-Item -LiteralPath $path
 if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked recovery resource refused'}
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256.ToUpperInvariant()){throw ('Recovery resource missing/changed: '+$entry.path)}
}
& (Join-Path $root 'Backend\HFBackend.exe') private-gui recover --job $Job
if($LASTEXITCODE){throw 'Recovery did not return a verified terminal response; retain all state.'}
'''.replace('__MANIFEST__',hashlib.sha256(raw).hexdigest().upper())
(OUT/'Recover.ps1').write_text(helper)
resources=specs+[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (OUT/'Resources.json',OUT/'Recover.ps1')]
bundle=digest(dict(scope=scope,resources=resources))[:16]
def quote(s):return s.replace("'","''")
files=[]
for r in resources:
 name=Path(r['path']);parent=name.parent.as_posix().replace('/','\\');dest='{tmp}\\VRKMI8A'+('\\'+parent if parent!='.' else '')
 files.append('Source: "'+str(OUT/name)+'"; DestDir: "'+dest+'"; Flags: dontcopy')
(BUILD/'files.iss').write_text('\n'.join(files)+'\n')
lines=['const',"  ResourceBundle = '"+bundle+"';", "  PersistentSuffix = '"+quote(scope)+"';",'  ResourceCount = '+str(len(resources))+';', 'var','  ResourceNames, ResourceHashes: array[0..'+str(len(resources)-1)+'] of String;', 'procedure InitResourceList;','begin']
for i,r in enumerate(resources):
 name=quote(r['path'].replace('/',chr(92)))
 lines+=[f"  ResourceNames[{i}] := '{name}';",f"  ResourceHashes[{i}] := '{r['sha256']}';"]
lines+=['end;'];(BUILD/'resources.iss').write_text('\n'.join(lines))
(BUILD/'single.iss').write_text('#define SINGLE_EXE\n#define EmbeddedFiles "'+str(BUILD/'files.iss')+'"\n#define EmbeddedResources "'+str(BUILD/'resources.iss')+'"\n#include "'+str(W/'src/installer/ui-prototype/preview.iss')+'"\n')
result=dict(kind=kind,scope=scope,bundle=bundle,resources=resources,build=str(BUILD),output=str(OUT),qualification=a.qualification)
(REPORT/(kind+'-bundle.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='resources'},indent=2))
