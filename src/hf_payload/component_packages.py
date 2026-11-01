"""Bounded package verification and file mappings; no game target or payload execution."""
import hashlib,stat,zipfile
from pathlib import Path
from .validator import safe_relative,stable_hash,no_links
from .recovery import SafetyError
from .release_scope import selection_errors

PACKAGES={
'BepInEx_x64_5.4.12.0.zip':'bepinex',
'BepInEx.ConfigurationManager_v16.3.zip':'configuration-manager',
'BepInEx.MessageCenter.v1.1.1.zip':'message-center',
'XUnity.ResourceRedirector-BepIn-5x-1.1.3.zip':'resource-redirector',
'VRK_PlayWithoutVR v1.0.0.0.zip':'play-without-vr',
'VRK_UncensorLoader v1.0.0.0.zip':'uncensor-loader',
'BepInEx.MuteInBackground.v1.1.zip':'mute',
'GraphicsSettings.dll':'graphics','FPSCounter_v3.1.zip':'fps',
'RuntimeUnityEditor_BepInEx5_v2.4.zip':'runtime-editor','ScriptLoader.dll':'script-loader',
'VRKanojo_Plugins-1.0.zip':None,'BepInEx.ConfigurationManager-16.3.zip':None}

def inspect_package(path):
 path=Path(path);size,sha=stable_hash(path);entries=[];names=set();total=0
 if path.name not in PACKAGES:raise SafetyError('unrecognized package name')
 if path.suffix.lower()=='.zip':
  with zipfile.ZipFile(path) as z:
   if len(z.infolist())>2000:raise SafetyError('archive entry bound exceeded')
   for i in z.infolist():
    name=safe_relative(i.filename.rstrip('/'));fold=name.casefold()
    if fold in names or (i.external_attr>>16)&0o170000==stat.S_IFLNK or i.flag_bits&1:raise SafetyError('duplicate/link/encrypted entry')
    names.add(fold)
    if i.is_dir():continue
    total+=i.file_size
    if total>64*1024*1024 or i.file_size>16*1024*1024:raise SafetyError('archive size bound exceeded')
    raw=z.read(i) # CRC checked by ZipFile
    entries.append({'path':name,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 else:entries=[{'path':'BepInEx/plugins/'+path.name,'size':size,'sha256':sha}]
 if stable_hash(path)!=(size,sha):raise SafetyError('package changed during inspection')
 return {'name':path.name,'size':size,'sha256':sha,'files':entries,'component':PACKAGES.get(path.name)}

def stage_package(path,root,record):
 """Private verification staging only, no production eligibility granted."""
 path=Path(path);root=Path(root);no_links(root)
 if record.get('component') is None:raise SafetyError('source reference archives cannot become runtime payloads')
 if inspect_package(path)!=record:raise SafetyError('package review changed')
 base=root/record['component'];base.mkdir(exist_ok=False)
 with zipfile.ZipFile(path) if path.suffix.lower()=='.zip' else open(path,'rb') as source:
  for f in record['files']:
   p=base/safe_relative(f['path']);p.parent.mkdir(parents=True,exist_ok=True);no_links(p.parent)
   raw=source.read(f['path']) if isinstance(source,zipfile.ZipFile) else source.read()
   if len(raw)!=f['size'] or hashlib.sha256(raw).hexdigest()!=f['sha256']:raise SafetyError('source hash changed')
   with p.open('xb') as out:out.write(raw)
   if stable_hash(p)!=(f['size'],f['sha256']):raise SafetyError('staged hash mismatch')
 return base

def select_runtime(catalog, selected, desktop_mode, existing=()):
 """Local fixture-file selection only. This grants no redistribution/game eligibility."""
 if desktop_mode not in ('neither','vrkanojo-desktop','play-without-vr'):raise SafetyError('invalid desktop mode')
 if type(selected) is not list or len(selected)!=len(set(selected)):raise SafetyError('invalid selections')
 chosen=set(selected)
 if chosen.intersection({'vrkanojo-desktop','play-without-vr'})-({desktop_mode} if desktop_mode!='neither' else set()):raise SafetyError('desktop mode disagrees with component selection')
 if desktop_mode!='neither':chosen.add(desktop_mode)
 if {'vrkanojo-desktop','play-without-vr'}<=chosen:raise SafetyError('desktop plugins conflict')
 for name in existing:
  name=safe_relative(name).split('/')[-1].casefold()
  if name=='vrk_playwithoutvr.dll' and 'vrkanojo-desktop' in chosen or name=='vrkanojodesktop.dll' and 'play-without-vr' in chosen:
   raise SafetyError('existing conflicting desktop plugin; separate ownership/backup/consent plan required')
 errors=selection_errors(catalog,chosen)
 if errors:raise SafetyError('; '.join(errors))
 components={c['id']:c for c in catalog['components']};rows=[];destinations=set()
 for required in catalog.get('runtime_required_components',['bepinex']):
  if required not in chosen:raise SafetyError('runtime profile requires '+required)
 for key in sorted(chosen):
  if key not in components:raise SafetyError('unknown component')
  c=components[key]
  if c.get('runtime_verification')!='local-files-verified':raise SafetyError('runtime component not qualified: '+key)
  if any(d not in chosen for d in c['dependencies']):raise SafetyError('missing dependency: '+key)
  for f in c['runtime_files']:
   safe_relative(f['staged_source'])
   destination=safe_relative(f['destination']);fold=destination.casefold()
   if fold in destinations:raise SafetyError('destination conflict')
   destinations.add(fold);rows.append(dict(f,component=key))
 return rows
