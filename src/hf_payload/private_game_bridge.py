"""Game bridge: checked target policy and per-plan consent, no automatic installation."""
import json,secrets,time,uuid
from .external_root import ExternalArea,ExternalCoordinator,qualify_private_copy,component_requests,STATE_ROOT
from .private_target import load_permit
from .private_credentials import crypt
from .recovery import WORKSPACE,canonical,digest,exclusive_bytes,read_json,SafetyError,present,shape
from .validator import no_links
from .registry import Registry
from .ownership import ReviewedPlan
from .planner import approval_key
from . import install_bridge
PROFILE='private-disposable-game-v1'
AUTHORITY=WORKSPACE/'out'/'private-authority'

def request_for(mask,desktop,target):
    from .real_file_bridge import request_for as validate
    validate(mask,desktop,'demo-a')
    if type(target) is not str or not target or any(c in target for c in '\0\r\n"'):raise SafetyError('invalid manual target')
    return dict(schema_version=1,profile=PROFILE,mask=mask,desktop=desktop,target=target,disposable_confirmed=True)

def prepare(request,clock=time.time):
    shape(request,'schema_version profile mask desktop target disposable_confirmed')
    if request['schema_version']!=1 or request['profile']!=PROFILE or request['disposable_confirmed'] is not True:
        raise SafetyError('explicit private disposable-target acknowledgement required')
    request_for(request['mask'],request['desktop'],request['target'])
    permit=load_permit();policy=permit.policy()
    # Keep old individually approved policies compatible; new policies qualify the manual selection.
    from pathlib import Path
    if policy['scope']=='private-disposable-game-test' and Path(request['target'])!=Path(policy['target']):raise SafetyError('only the specifically approved disposable directory may be selected')
    p=qualify_private_copy(request['target'],selected_manually=True,disposable_confirmed=True,
                          protected_roots=policy['protected_roots'],desktop=request['desktop'],
                          compatibility=policy['scope']=='compatible-original-game-v1')
    permit.check(p,full=True)
    selected=['bepinex','loader-config']
    if request['mask']&8:selected+=['message-center']
    if request['mask']&16:selected+=['mute']
    if request['mask']&32:selected+=['fps']
    if request['mask']&64:selected+=['graphics']
    keys=[secrets.token_bytes(32) for _ in range(4)]
    area=ExternalArea.enroll_private(p,digest(p),keys[0],permit)
    AUTHORITY.mkdir(exist_ok=True);no_links(AUTHORITY)
    credentials=dict(schema=1,scope=PROFILE,bridge_id=area.path.name,policy=permit.trusted_digest,profile=digest(p),keys=[k.hex() for k in keys])
    exclusive_bytes(AUTHORITY/(area.path.name+'.dpapi'),crypt(canonical(credentials)))
    rows=component_requests(area,selected,request['desktop'])
    if all(r['action']=='preserve' for r in rows):
        return dict(status='AlreadyPresent',profile=PROFILE,bridge_id=area.path.name,plan_digest='',
                    operations=[dict(action='preserve',path=r['destination'],before=r['before'],after=None) for r in rows],
                    summary='No changes required: all selected files/settings already match. No installation ran, no ownership was adopted, and unselected plugins were preserved.',
                    errors=[],real_installation_allowed=False)
    reg=Registry(area,*keys[1:3],clock=clock);reg.create();co=ExternalCoordinator(area,reg,keys[3])
    # These gates approve private byte-copy testing of the reviewed catalog only.
    # Public distribution/gameplay qualification is NOT granted by this test context.
    plan=reg.plan(rows,[approval_key(r) for r in rows],dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True))
    co._write_signed(area.path/'private-plan.json',dict(schema=1,profile=PROFILE,checkpoint=dict(reg.checkpoint),plan=plan.document,context=co.authorize(plan,plan.sha256)))
    return dict(status='PreparedAwaitingConsent',profile=PROFILE,bridge_id=area.path.name,plan_digest=plan.sha256,
         synthetic_root=str(area.target),operations=[dict(action=r['action'],path=r['destination'],before=r['before'],after=r['after']) for r in rows],
         summary='Selected game plan; exact game version unverified. No target changes until separate consent.',real_installation_allowed=True)

def _load(bridge_id,clock=time.time):
    if type(bridge_id) is not str or str(uuid.UUID(bridge_id))!=bridge_id:raise SafetyError('invalid private transaction ID')
    no_links(AUTHORITY)
    sealed=AUTHORITY/(bridge_id+'.dpapi');no_links(sealed)
    if sealed.stat().st_size>65536:raise SafetyError('oversized credential record')
    record=json.loads(crypt(sealed.read_bytes(),True));permit=load_permit()
    if record['schema']!=1 or record['scope']!=PROFILE or record['bridge_id']!=bridge_id or record['policy']!=permit.trusted_digest:
        raise SafetyError('credential scope/policy mismatch')
    keys=[bytes.fromhex(k) for k in record['keys']]
    if len(keys)!=4 or len(set(keys))!=4:raise SafetyError('independent private keys required')
    area=ExternalArea(STATE_ROOT/bridge_id,keys[0],record['profile'],permit)
    reg=Registry(area,*keys[1:3],clock=clock);co=ExternalCoordinator(area,reg,keys[3])
    body=co._read_signed(area.path/'private-plan.json')
    if body['profile']!=PROFILE:raise SafetyError('wrong plan scope')
    return area,reg,co,body,ReviewedPlan(body['plan'])

def _result(area,result):
    report=install_bridge._result(area,result)
    report.update(real_installation_allowed=True,profile=PROFILE,retained_created_directories=result.get('retained_created_directories',[]))
    report['summary']=('Private installation verified and committed. Gameplay/version compatibility remains unverified.'
                      if report['status']=='CommittedSynthetic' else 'Private installation did not commit; review recovery status and preserve records.')
    return report

def execute(bridge_id,approved_plan,clock=time.time,fault=lambda point,index:None):
    area,reg,co,body,plan=_load(bridge_id,clock)
    with area.lock():
        if approved_plan!=plan.sha256:raise SafetyError('exact private plan approval required')
        if present(co.intent) or present(area.path/'private-consent.json'):raise SafetyError('execution attempted; recover instead of replay')
        reg.open(body['checkpoint']);token=reg.issue(plan,approved_plan)
        co._write_signed(area.path/'private-consent.json',dict(profile=PROFILE,plan=plan.sha256,token=token))
        return _result(area,co.execute(plan,token,body['context'],fault))

def recover(bridge_id,clock=time.time,fault=lambda point,index:None):
    area,reg,co,body,plan=_load(bridge_id,clock)
    with area.lock():return _result(area,co.resume(body['checkpoint'],fault))
