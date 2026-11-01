"""Read-only controlled game selection gate. Never adopts a game as SyntheticArea."""
import os
from pathlib import Path
from .detection import detect,LAYOUTS,desktop_compatibility
from .recovery import SyntheticArea,SafetyError,digest
from .validator import no_links


def _within(path,parent):
 return path==parent or parent in path.parents


def qualify_selection(raw_path, *, selected_manually=False, disposable_confirmed=False,
                      protected_roots=None, profiles=(), trusted_profiles=frozenset(),
                      desktop='neither',fixture_area=None):
 """No auto-scan. Protection/profile gates precede target reads.

    Caller-supplied fixture pins qualify tests only. A recognized layout or checkbox
    does not authorize writes, grant ownership, or turn local metadata into provenance.
    """
 result={'schema_version':1,'scope':'controlled-game-read-only','detection':None,'blockers':[],
         'installation_allowed':False,'execution_authorized':False,'target_inspected':False,
         'recognized_candidate_layouts':[{'exe':e,'data':d} for e,d in LAYOUTS]}
 def blocked(message):result['blockers'].append(message);result['status']='Blocked';return result
 if not selected_manually:return blocked('Explicit manual folder selection required; no game is silently selected.')
 if not disposable_confirmed:return blocked('Explicit disposable-copy acknowledgement required; it is not provenance or execution consent.')
 if type(raw_path) is not str or not raw_path or raw_path!=raw_path.strip() or any(c in raw_path for c in ('\0','\n','\r','"')):return blocked('Invalid path text.')
 root=Path(raw_path)
 if not root.is_absolute() or str(root).startswith(('\\\\','//')) or root.parent==root:return blocked('Select an absolute local disposable directory, not a drive root, network path or relative path.')
 root=Path(os.path.abspath(root));result['selected_root']=str(root)
 if root.parent==root:return blocked('Normalized drive root is not a disposable game directory.')
 if any(p.casefold()=='steamapps' for p in root.parts):return blocked('Steam-library locations are protected. Select a separately prepared copy outside the library.')
 if protected_roots is None:return blocked('Protected original-installation path policy is not established; no target files inspected.')
 if any(_within(root,Path(os.path.abspath(p))) or _within(Path(os.path.abspath(p)),root) for p in protected_roots):return blocked('Selection overlaps a protected installation; no target files inspected.')
 if fixture_area is not None:
  try:area=SyntheticArea(fixture_area.path)
  except (OSError,ValueError) as exc:return blocked('Invalid engine-created fake-game fixture: '+str(exc))
  if root!=area.target:return blocked('Test authorization is bound only to the designated fake-game fixture.')
  result['scope']='controlled-fake-game-test'
 if not profiles or not trusted_profiles:return blocked('No independently approved original-2018 v1.31 fingerprint profile is available; no target files inspected.')
 # Require every supplied reference to be separately pinned before the detector reads anything.
 if any(digest(p) not in trusted_profiles for p in profiles):return blocked('Untrusted game profile; no target files inspected.')
 result['target_inspected']=True
 detection=detect(root,profiles,trusted_profiles);result['detection']=detection
 if detection['status']!='supported':return blocked(detection['validation_message']+' '+ '; '.join(detection['reasons']))
 if any(m.casefold() in ('ali21364.dll','startconfig.xml') for m in detection['markers']):return blocked('Nonstandard game markers require separate provenance/compatibility review; preserve files unchanged.')
 compatibility=desktop_compatibility(detection,desktop)
 if compatibility['blockers']:return blocked('; '.join(compatibility['blockers']))
 if fixture_area is None:return blocked('Fingerprint matched, but external game-root transactions and original-installation protection are not qualified. SyntheticArea cannot be used as a bypass.')
 result['status']='QualifiedFakeGameFixture';result['blockers'].append('Fixture qualification only; real-game installation remains disabled.')
 return result


def authorize_game_installation(report):
 """A deliberate fail-closed boundary until the external-root engine is qualified."""
 raise SafetyError('Real game-root execution is not implemented/qualified; no installation token can be issued.')
