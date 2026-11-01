"""Prepare only an application-local Python build environment from hash-pinned inputs."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
VERSION='3.14.10'
EXPECTED='90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--wheels',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
w=Path(__file__).resolve().parents[1]
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if h(a.archive)!=EXPECTED:raise SystemExit('Official Python archive hash mismatch')
if a.destination.exists():raise SystemExit('Refusing existing build environment')
lock=(w/'build-requirements.txt').read_text()
wheelpaths=sorted(a.wheels.glob('*.whl'))
if len(wheelpaths)!=7 or any(h(f) not in lock for f in wheelpaths):raise SystemExit('Pinned build wheels missing or changed')
def unpack(archive,destination):
 with zipfile.ZipFile(archive) as z:
  for i in z.infolist():
   path=Path(i.filename)
   if path.is_absolute() or '..' in path.parts or ':' in i.filename or '\\' in i.filename:raise ValueError('Unsafe archive path')
  z.extractall(destination)
unpack(a.archive,a.destination)
# Verify publisher before ever running the downloaded interpreter. The .ps1 path is an argument, not shell interpolation.
ps=Path(__import__('os').environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
verify=a.destination/'verify-publisher.ps1'
verify.write_text("param([string]$Runtime)\n$ErrorActionPreference='Stop'\nImport-Module ($PSHOME+'\\Modules\\Microsoft.PowerShell.Security\\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop\nforeach($name in @('python.exe','python314.dll')){$s=Get-AuthenticodeSignature -LiteralPath (Join-Path $Runtime $name);if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'CN=Python Software Foundation,'){throw 'Python publisher verification failed'}}\n")
subprocess.run([str(ps),'-NoProfile','-NonInteractive','-File',str(verify),str(a.destination.resolve())],check=True)
site=a.destination/'Lib/site-packages';site.mkdir(parents=True)
for f in wheelpaths:unpack(f,site)
unpack(a.destination/'python314.zip',a.destination/'Lib')
(a.destination/'python314._pth').write_text('python314.zip\n.\nLib\nLib/site-packages\nimport site\n')
print(json.dumps(dict(python=str(a.destination/'python.exe'),version=VERSION,archive_sha256=EXPECTED)))

