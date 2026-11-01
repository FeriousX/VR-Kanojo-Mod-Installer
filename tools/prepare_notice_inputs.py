from pathlib import Path
import shutil
w=Path(__file__).resolve().parents[1]
out=w/'out/Portable Backend/HFBackend/Notices'
if out.exists():raise SystemExit('Refusing to overwrite existing notice inputs')
out.mkdir(parents=True)
for name in ('CPython-LICENSE.txt','PyInstaller-COPYING.txt'):
 shutil.copyfile(w/'third_party/licenses'/name,out/name)
r=w/'payload/component-review/_notices_reference/vrk-plugins'
r.mkdir(parents=True,exist_ok=False)
shutil.copyfile(w/'third_party/licenses/vrk-plugins-LICENSE.txt',r/'LICENSE')
(r/'README.md').write_text('Original VRKanojo plugins by ManlyMarco: https://github.com/ManlyMarco/VRKanojo_Plugins\n')
print('Reference inputs prepared. This does not clear binary redistribution or authorize a release.')

for source in sorted((w/'third_party/licenses/essential').iterdir()):
 if source.is_file():
  shutil.copyfile(source,out/source.name)
print('Essential notices copied into the existing embedded Notices input directory. Runtime notices copied; separate artifact qualification is required.')

shutil.copytree(w/"third_party/licenses/runtime-3.14.10",out/"Runtime-3.14.10")
