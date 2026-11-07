"""Real-byte fixture preparation; execution/recovery reuse the existing install bridge."""
import json,secrets,shutil,sys,time
from pathlib import Path
from . import install_bridge as original
from .component_packages import select_runtime
from .real_components import catalog_digest,validate_catalog
from .recovery import SyntheticArea,stable_hash,snapshot,digest,canonical,exclusive_bytes,SafetyError,read_json
from .registry import Registry
from .coordinator import Coordinator
from .planner import approval_key
from .validator import no_links
PROFILE='real-component-fixture-v1'

def load_catalog():
 if getattr(sys,'frozen',False):
  from real_payload_pin import CATALOG_DIGEST
  root=Path(sys.executable).absolute().parent/'Components';catalog=read_json(root/'catalog.json');expected=CATALOG_DIGEST
 else:
  root=Path(__file__).resolve().parents[2]/'payload'
  catalog=read_json(root.parent/'manifests/real-components.json');expected=read_json(root.parent/'manifests/real-components.review.json')['catalog_digest']
 no_links(root);validate_catalog(catalog)
 if catalog_digest(catalog)!=expected:raise SafetyError('component catalog changed; reviewed rebuild required')
 return catalog,root

def request_for(mask,desktop,library):
 if type(mask) is not int or mask<0 or mask & ~121 or not mask&1:raise SafetyError('framework/settings are mandatory; invalid mask')
 if library not in ('demo-a','demo-b'):raise SafetyError('only disposable fixture labels are allowed')
 if desktop not in ('neither','vrkanojo-desktop','play-without-vr'):raise SafetyError('invalid desktop mode')
 return dict(schema_version=1,action=PROFILE,mask=mask,desktop_mode=desktop,demo_library=library)

def prepare(request,clock=time.time):
 if type(request) is not dict or set(request)!=set(('schema_version','action','mask','desktop_mode','demo_library')) or request['schema_version']!=1 or request['action']!=PROFILE:raise SafetyError('invalid real-fixture request')
 request_for(request['mask'],request['desktop_mode'],request['demo_library'])
 catalog,source=load_catalog();selected=['bepinex','loader-config']
 if request['mask']&8:selected+=['message-center']
 if request['mask']&16:selected+=['mute']
 if request['mask']&32:selected+=['fps']
 if request['mask']&64:selected+=['graphics']
 rows=select_runtime(catalog,selected,request['desktop_mode'])
 # Validate every selected file before creating the fixture. No UI destination input exists.
 for f in rows:
  if stable_hash(source/f['staged_source'])!=(f['size'],f['sha256']):raise SafetyError('missing or changed component: '+f['destination'])
 area=SyntheticArea.create();(area.path/'payload').mkdir();owner='real-gui-fixture'
 for f in rows:
  target=area.path/'payload'/f['destination'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/f['staged_source'],target)
  if stable_hash(target)!=(f['size'],f['sha256']):raise SafetyError('fixture copy verification failed')
  (area.target/f['destination']).parent.mkdir(parents=True,exist_ok=True)
 # Explicit fixture-owned seed exercises backup/replacement. No runtime file installed yet.
 (area.target/'doorstop_config.ini').write_bytes(b'; disposable fixture seed, not a game configuration\n')
 (area.target/'unrelated.txt').write_bytes(b'Unowned fixture guard: preserve.\n')
 keys=[secrets.token_bytes(32) for _ in range(3)]
 exclusive_bytes(area.path/'bridge-keys.json',canonical({'scope':'synthetic-bridge-only','area':area.path.name,'keys':[k.hex() for k in keys]}))
 reg=Registry(area,*keys[:2],clock=clock);reg.create();before=snapshot(area.target/'doorstop_config.ini')
 receipt=dict(schema=1,installation='fixture-bootstrap',owner=owner,area=area.path.name,target_id=area.marker['target_id'],parent=None,files=[{'path':'doorstop_config.ini','expected':{k:before[k] for k in ('size','sha256')}}])
 anchor=reg.anchor_request([receipt],{digest(receipt)},{digest(receipt)});reg.update_trust(anchor,reg.approve_anchor(anchor,digest(anchor)))
 requests=[]
 for f in rows:
  state=snapshot(area.target/f['destination']);requests.append(dict(destination=f['destination'],source=f['destination'],action='replace' if state['exists'] else 'create',owner=owner,before={k:state[k] for k in ('size','sha256')} if state['exists'] else None,after={k:f[k] for k in ('size','sha256')}))
 # Private test-only authorization as in Phase 6C.2; never a distribution/game grant.
 plan=reg.plan(requests,[approval_key(r) for r in requests],dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True));co=Coordinator(area,reg,keys[2])
 co._write_signed(area.path/'bridge-plan.json',dict(schema=1,scope='synthetic-bridge-only',bridge_id=area.path.name,checkpoint=dict(reg.checkpoint),plan=plan.document,context=co.authorize(plan,plan.sha256)))
 exclusive_bytes(area.path/'real-component-fixture.json',canonical({'profile':PROFILE,'selected':selected,'desktop_mode':request['desktop_mode'],'catalog_digest':catalog_digest(catalog)}))
 return dict(status='PreparedAwaitingConsent',profile=PROFILE,bridge_id=area.path.name,plan_digest=plan.sha256,synthetic_root=str(area.target),
  operations=[{'action':r['action'],'path':r['destination'],'before':r['before'],'after':r['after']} for r in requests],
  summary='Private real-component file-copy fixture; no game access or redistribution clearance.',real_installation_allowed=False)

execute=original.execute
recover=original.recover
status=original.status
