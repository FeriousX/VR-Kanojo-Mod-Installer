"""Package only the reviewed corresponding-source allowlist. Never installs files."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
W=Path(__file__).resolve().parents[1];sys.path[:0]=[str(W/'src'),str(W/'tools')]
from release_config import load_final_config,source_export_plan
from hf_payload.validator import no_links

def package(root=W):
 root=Path(root);cfg=load_final_config(root);rows=source_export_plan(root)
 distribution=root/cfg['distribution_dir'];no_links(distribution)
 stage=distribution/'Source/VR-Kanojo-Mod-Installer';archive=distribution/cfg['source_name']
 if stage.exists() or archive.exists():raise FileExistsError('Refusing source export/archive overwrite')
 stage.mkdir(parents=True,exist_ok=False)
 for row in rows:
  source=root/row['path'];no_links(source);raw=source.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('source changed during export')
  dest=stage/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('source export copy mismatch')
 sums=''.join(r['sha256']+'  '+r['path']+'\n' for r in sorted(rows,key=lambda r:r['path']))
 (stage/'SOURCE_SHA256SUMS.txt').write_text(sums,encoding='utf-8')
 files=sorted(p for p in stage.rglob('*') if p.is_file())
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:
   name='VR-Kanojo-Mod-Installer/'+p.relative_to(stage).as_posix()
   entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
   z.writestr(entry,p.read_bytes())
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None or len(z.namelist())!=len(files):raise ValueError('source archive verification failed')
  for p in files:
   if z.read('VR-Kanojo-Mod-Installer/'+p.relative_to(stage).as_posix())!=p.read_bytes():raise ValueError('source archive member changed')
 return {'source_archive':str(archive),'source_root':str(stage),'source_files':len(files),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest().upper()}
if __name__=='__main__':print(json.dumps(package(),indent=2))
