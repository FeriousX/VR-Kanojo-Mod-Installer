"""Standalone synthetic install bridge; GUI execution deliberately remains disconnected."""
import hashlib
import secrets
import time
import uuid
from .ui_adapter import new_fixture, validate_selection, CATALOG
from .coordinator import Coordinator
from .ownership import ReviewedPlan
from .planner import approval_key
from .registry import Registry
from .recovery import BASE, SyntheticArea, SafetyError, digest, read_json, exclusive_bytes, canonical, shape, present


def _spec(raw):
    return {'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def prepare(request, clock=time.time):
    area=new_fixture()
    gates=dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True)
    validation=validate_selection(request,area,gates)
    if validation['status'] != 'valid' or not validation['operations']:
        return {'status':'Blocked','bridge_id':area.path.name,'summary':validation['summary'],
                'errors':validation['conflicts'] or ['No mutable selection'], 'real_installation_allowed':False}
    # New fixture-owned preimage exercises the real backup/replace path, not real assets.
    owner='ui-synthetic-fixture'
    previous=b'Previous authored synthetic framework example.\n'
    core='core-framework' in request['components']
    if core: (area.target/'proposal/core-framework.txt').write_bytes(previous)
    (area.target/'unrelated.txt').write_bytes(b'Unowned synthetic user text - preserve.\n')
    keys=[secrets.token_bytes(32) for _ in range(3)]
    exclusive_bytes(area.path/'bridge-keys.json',canonical({'scope':'synthetic-bridge-only','area':area.path.name,
                    'keys':[key.hex() for key in keys]}))
    registry=Registry(area,keys[0],keys[1],clock=clock); registry.create()
    if core:
        receipt=dict(schema=1,installation='fixture-bootstrap',owner=owner,area=area.path.name,
                     target_id=area.marker['target_id'],parent=None,
                     files=[{'path':'proposal/core-framework.txt','expected':_spec(previous)}])
        req=registry.anchor_request([receipt],{digest(receipt)},{digest(receipt)})
        registry.update_trust(req,registry.approve_anchor(req,digest(req)))
    selected=validation['selected_components']+([] if validation['desktop_mode']=='neither' else [validation['desktop_mode']])
    rows=[]
    for key in selected:
        replacing=key=='core-framework' and core
        rows.append(dict(destination='proposal/'+key+'.txt',source=key+'.txt',action='replace' if replacing else 'create',
                         owner=owner,before=_spec(previous) if replacing else None,after=_spec(CATALOG[key])))
    plan=registry.plan(rows,[approval_key(row) for row in rows],gates)
    co=Coordinator(area,registry,keys[2])
    body={'schema':1,'scope':'synthetic-bridge-only','bridge_id':area.path.name,'checkpoint':dict(registry.checkpoint),
          'plan':plan.document,'context':co.authorize(plan,plan.sha256)}
    co._write_signed(area.path/'bridge-plan.json',body)
    return {'status':'PreparedAwaitingConsent','bridge_id':area.path.name,'plan_digest':plan.sha256,
            'synthetic_root':str(area.target),'operations':[{'action':r['action'],'path':r['destination'],
             'before':r['before'],'after':r['after']} for r in rows],
            'summary':'Review these exact synthetic text-file operations, then separately approve this plan digest.',
            'real_installation_allowed':False}


def _load(bridge_id, clock=time.time):
    if not isinstance(bridge_id,str) or str(uuid.UUID(bridge_id)) != bridge_id:
        raise SafetyError('invalid synthetic bridge ID; filesystem paths are forbidden')
    area=SyntheticArea(BASE/bridge_id)
    credentials=read_json(area.path/'bridge-keys.json')
    shape(credentials,'scope area keys')
    if credentials['scope']!='synthetic-bridge-only' or credentials['area']!=bridge_id or len(credentials['keys'])!=3:
        raise SafetyError('invalid synthetic credential record')
    keys=[bytes.fromhex(value) for value in credentials['keys']]
    registry=Registry(area,keys[0],keys[1],clock=clock)
    co=Coordinator(area,registry,keys[2])
    body=co._read_signed(area.path/'bridge-plan.json')
    shape(body,'schema scope bridge_id checkpoint plan context')
    if body['schema']!=1 or body['scope']!='synthetic-bridge-only' or body['bridge_id']!=bridge_id:
        raise SafetyError('plan belongs to another scope/root')
    return area,registry,co,body,ReviewedPlan(body['plan'])


def _result(area, result):
    status=result['status']
    report={'status':status,'bridge_id':area.path.name,'transaction_id':result.get('txid'),
            'real_installation_allowed':False,'percent':100 if status=='CommittedSynthetic' else None,
            'completed_operations':[],'backups_verified':False,'errors':[]}
    if result.get('txid'):
        from .recovery import Transaction
        tx=Transaction(area,result['txid']); manifest=tx.verify()
        report['backups_verified']=True
        report['journal_state']=tx.inspect()['state']
        report['errors']=tx.inspect()['errors']
        if status=='CommittedSynthetic':
            report['completed_operations']=[{'action':r['action'],'path':r['path']} for r in manifest['plan'] if r['action']!='protect']
    report['summary']=('Synthetic installation verified and acknowledged.' if status=='CommittedSynthetic'
                       else 'Synthetic transaction did not commit. Review status, journal and recovery errors.')
    return report


def execute(bridge_id, approved_plan, clock=time.time, fault=lambda point,index:None):
    area,registry,co,body,plan=_load(bridge_id,clock)
    if approved_plan!=plan.sha256: raise SafetyError('explicit matching plan consent required')
    if present(co.intent) or present(area.path/'bridge-consent.json'):
        raise SafetyError('execution already attempted; use recovery, never repeat execution')
    registry.open(body['checkpoint'])
    token=registry.issue(plan,approved_plan)  # fresh expiring consent, separate from validation
    co._write_signed(area.path/'bridge-consent.json',{'scope':'synthetic-bridge-only','plan':plan.sha256,'token':token})
    return _result(area,co.execute(plan,token,body['context'],fault))


def recover(bridge_id, clock=time.time, fault=lambda point,index:None):
    area,registry,co,body,plan=_load(bridge_id,clock)
    return _result(area,co.resume(body['checkpoint'],fault))


def status(bridge_id, clock=time.time):
    area,registry,co,body,plan=_load(bridge_id,clock)
    sessions=list(area.sessions.iterdir())
    if not sessions:
        return {'status':'AttemptedNoSession' if present(co.intent) or present(area.path/'bridge-consent.json') else 'PreparedAwaitingConsent',
                'bridge_id':bridge_id,'real_installation_allowed':False,'percent':None}
    if len(sessions)!=1: raise SafetyError('ambiguous transaction sessions')
    from .recovery import Transaction
    tx=Transaction(area,sessions[0].name)
    info=tx.inspect()
    # Completed file writes alone are not an ownership/acknowledgement success claim.
    return {'status':'NeedsReconciliation','bridge_id':bridge_id,'transaction_id':tx.txid,
            'journal':info,'real_installation_allowed':False,'percent':None}
