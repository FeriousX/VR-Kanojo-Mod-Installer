"""Prepare qualified notice inputs only; never runs a compiler or installer."""
from pathlib import Path
import argparse,shutil,sys
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'src'))
from hf_payload.validator import no_links

def prepare(destination):
 destination=Path(destination).absolute();no_links(destination.parent);destination=destination.resolve(strict=False)
 if not destination.is_relative_to(W/'out'):raise ValueError('notice staging must stay under this source workspace/out')
 destination.mkdir(parents=True,exist_ok=False)
 for name in ('CPython-LICENSE.txt','PyInstaller-COPYING.txt'):
  shutil.copyfile(W/'third_party/licenses'/name,destination/name)
 for source in (W/'third_party/licenses/essential').iterdir():
  if source.is_file():no_links(source);shutil.copyfile(source,destination/source.name)
 shutil.copytree(W/'third_party/licenses/runtime-3.14.10',destination/'Runtime-3.14.10')
 reference=destination/'ComponentReference/vrk-plugins';reference.mkdir(parents=True)
 shutil.copyfile(W/'third_party/licenses/vrk-plugins-LICENSE.txt',reference/'LICENSE')
 (reference/'README.md').write_text('Original VRKanojo plugins by ManlyMarco: https://github.com/ManlyMarco/VRKanojo_Plugins\nHistorical attribution only; excluded plugins are not installed.\n',encoding='utf-8')
 return destination
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);print(prepare(p.parse_args().destination))
