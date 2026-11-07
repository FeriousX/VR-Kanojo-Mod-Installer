"""Standalone frozen-backend qualification; synthetic jobs only, no game APIs."""
import argparse,hashlib,json,os,shutil,subprocess,time,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--report',required=True);args=p.parse_args()
bundle=Path(args.bundle).resolve();report=Path(args.report).resolve();stage=report/'Standalone test with spaces';stage.mkdir(exist_ok=False)
shutil.copytree(bundle/'Backend',stage/'Backend');exe=stage/'Backend/HFBackend.exe'
env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','_PYI_'))}
env['PATH']=str(Path(os.environ['SystemRoot'])/'System32');env['PYTHONHOME']=str(stage/'No Python');env['PYTHONPATH']=str(stage/'No Source')
checks=[];jobs=[]
def check(name,truth):
 if not truth:raise AssertionError(name)
 checks.append(name)
def call(args):return subprocess.run([str(exe),*args],env=env,cwd=stage,capture_output=True,text=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
def read(path):return json.loads(path.read_text(encoding='utf-8'))
version=call(['--version']);check('Standalone startup without external Python',version.returncode==0)
version=json.loads(version.stdout);state=Path(version['state_root']);check('Frozen qualified Python and package-only module origins',version['frozen'] and version['python'].startswith('3.14.10') and all(Path(x).is_relative_to(stage/'Backend') for x in version['module_origins'].values()))
check('Persistent state is outside package/extraction',not state.is_relative_to(stage) and state.name=='state')
def prepare(mask,desktop='neither',success=True):
 job=uuid.uuid4().hex*2;result=call(['real-gui','prepare','--job',job,'--mask',str(mask),'--desktop',desktop,'--library','demo-a'])
 if not success:return result
 if result.returncode:raise AssertionError(result.stdout+result.stderr)
 folder=state/'out/gui-install'/job;meta=read(folder/'job.json');target=Path(meta['prepared']['synthetic_root'])
 if not target.is_relative_to(state/'out/synthetic'):raise AssertionError('non-synthetic target')
 jobs.append(dict(job=job,folder=str(folder),target=str(target),mask=mask,desktop=desktop))
 return job,folder,meta,target
for mask in tuple(1|x for x in range(0,128,8)):
 job,folder,meta,target=prepare(mask);paths={x['path'] for x in meta['prepared']['operations']}
 check('Independent selection mask '+str(mask),all(('BepInEx/plugins/'+name in paths)==bool(mask&bit) for bit,name in ((8,'BepInEx.MessageCenter.dll'),(16,'BepInEx.MuteInBackground.dll'),(32,'FPSCounter.dll'),(64,'GraphicsSettings.dll'))))
 frame=read(folder/'frame.json');check('Hashed backend plan '+str(mask),all(row['after']['sha256'] in ' '.join(str(x) for x in frame.values()) for row in meta['prepared']['operations']))
for mask,mode in ((1,'neither'),(121,'vrkanojo-desktop')):
 job,folder,meta,target=prepare(mask,mode)
 before=call(['real-gui','run','--job',job,'--approve-plan','0'*64]);check('Consent refusal '+str(mask),before.returncode!=0 and not (target.parent/'coordinator-intent.json').exists())
 result=call(['real-gui','run','--job',job,'--approve-plan',meta['plan_digest']]);frame=read(folder/'frame.json')
 check('Verified commit '+str(mask),result.returncode==0 and frame['success']=='1' and frame['state']=='Completed')
 check('All installed hashes '+str(mask),all(hashlib.sha256((target/row['path']).read_bytes()).hexdigest()==row['after']['sha256'] for row in meta['prepared']['operations']))
 check('Unknown file preserved '+str(mask),(target/'unrelated.txt').read_bytes()==b'Unowned fixture guard: preserve.\n')
 resultfiles=list(folder.glob('*-result.json'));detail=read(max(resultfiles,key=lambda x:x.stat().st_mtime_ns))
 check('Backup verification '+str(mask),detail['backups_verified'] and detail['status']=='CommittedSynthetic')
 saved=(folder/'frame.json').read_bytes();repeat=call(['real-gui','run','--job',job,'--approve-plan',meta['plan_digest']]);check('Duplicate execution refused '+str(mask),repeat.returncode!=0 and (folder/'frame.json').read_bytes()==saved)
 recovery=call(['real-gui','recover','--job',job]);check('Fresh-process committed recovery '+str(mask),recovery.returncode==0 and read(folder/'frame.json')['success']=='1')
# Corrupt only disposable copied resources; restore them, never alter the input bundle.
cat=stage/'Backend/Components/catalog.json';raw=cat.read_bytes()
try:
 c=json.loads(raw);c['unexpected']='tampered';cat.write_text(json.dumps(c));result=prepare(1,success=False)
 check('Catalog tampering rejected',result.returncode!=0)
finally:cat.write_bytes(raw)
c=read(cat);fps=next(x for x in c['components'] if x['id']=='fps')['runtime_files'][0];dll=stage/'Backend/Components'/fps['staged_source'];raw=dll.read_bytes()
try:
 dll.write_bytes(b'changed');check('FPS payload tampering rejected',prepare(33,success=False).returncode!=0)
finally:dll.write_bytes(raw)
graphics=next(x for x in c['components'] if x['id']=='graphics')['runtime_files'][0]
gdll=stage/'Backend/Components'/graphics['staged_source'];graw=gdll.read_bytes()
try:
 gdll.write_bytes(b'changed graphics');check('Graphics payload tampering rejected',prepare(65,success=False).returncode!=0)
finally:gdll.write_bytes(graw)
job,folder,meta,target=prepare(33);source=target.parent/'payload/BepInEx/plugins/FPSCounter.dll';source.write_bytes(b'changed prepared synthetic payload')
result=call(['real-gui','run','--job',job,'--approve-plan',meta['plan_digest']]);frame=read(folder/'frame.json')
check('Execution-time tampering fails closed',frame['success']=='0' and frame['state']!='Completed' and not (target/'BepInEx/plugins/FPSCounter.dll').exists())
check('No pre-existing target changed on refusal',(target/'doorstop_config.ini').read_bytes()==b'; disposable fixture seed, not a game configuration\n')
for row in read(bundle/'Resources.json')['files']:
 if row['path'].startswith('Backend/'):
  actual=stage/row['path'];check('Resource restored: '+row['path'],hashlib.sha256(actual.read_bytes()).hexdigest()==row['sha256'])
(report/'packaged-tests.json').write_text(json.dumps(dict(status='PASS',checks_passed=len(checks),checks=checks,jobs=jobs,version=version,game_access=False,gui_launched=False),indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',checks_passed=len(checks),jobs=len(jobs),backend=str(exe))))
