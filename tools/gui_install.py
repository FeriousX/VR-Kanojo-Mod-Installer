"""Version-1 fixed-root GUI transport; synthetic prepare/run/recover only."""
import argparse
import configparser
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hf_payload import install_bridge as bridge
from hf_payload.recovery import canonical, exclusive_bytes, read_json, SafetyError
from hf_payload.validator import no_links
from wizard_validate import request_for
from hf_payload.transport.presentation import presentation
from hf_payload.runtime_paths import workspace

WORKSPACE=workspace()
EXCHANGE=WORKSPACE/'out'/'gui-install'
TRANSPORT_SCOPE='synthetic-gui-bridge'
REAL_ALLOWED='0'


def folder_for(job):
    if not isinstance(job,str) or not re.fullmatch('[0-9a-f]{64}',job): raise SafetyError('invalid GUI job ID')
    no_links(EXCHANGE)
    folder=EXCHANGE/job; no_links(folder)
    return folder


def publish(folder,meta,state,lines,final=False,success=False):
    allowed=('Prepared','Blocked','Validating','BackingUp','Applying','Verifying','Completed','Failed','RecoveryRequired')
    if state not in allowed or type(final) is not bool or final and state not in ('Blocked','Completed','Failed','RecoveryRequired'):
        raise SafetyError('invalid state frame')
    if type(success) is not bool or success and (not final or state!='Completed'):
        raise SafetyError('invalid success frame')
    if state=='Completed' and not success: raise SafetyError('completion requires verified success')
    if len(lines)>40 or any(not isinstance(s,str) or len(s)>2000 or '\n' in s or '\r' in s for s in lines):
        raise SafetyError('invalid display frame')
    frame=dict(protocol='1',scope=TRANSPORT_SCOPE,job=meta['job'],binding=meta['binding'],
               bridge_id=meta.get('bridge_id',''),plan_digest=meta.get('plan_digest',''),state=state,
               final='1' if final else '0',success='1' if success else '0',real_installation_allowed=REAL_ALLOWED,
               percent='100' if success else '',sequence=str(time.time_ns()),count=str(len(lines)))
    display=presentation(meta,state,success)
    if any(type(value) is not str or len(value)>2000 or '\n' in value or '\r' in value for value in display.values()):
        raise SafetyError('invalid presentation frame')
    frame.update(display)
    frame.update({'line'+str(i):s for i,s in enumerate(lines)})
    if meta.get('profile'):frame['profile']=meta['profile']
    raw=canonical(frame)
    config=configparser.ConfigParser(interpolation=None)
    config['transaction']={**frame,'response_sha256':hashlib.sha256(raw).hexdigest()}
    text=io.StringIO();config.write(text)
    for name,data in (('frame.json',raw),('frame.ini',text.getvalue().encode('ascii','backslashreplace'))):
        tmp=folder/(str(uuid.uuid4())+'.tmp');exclusive_bytes(tmp,data)
        no_links(folder/name) if (folder/name).exists() else no_links(folder)
        # Windows readers may briefly deny delete-sharing. Retry publication,
        # never write through an open reader or weaken transaction verification.
        for attempt in range(20):
            try:
                os.replace(tmp,folder/name)
                break
            except PermissionError:
                if attempt==19: raise
                time.sleep(.01)


@contextmanager
def worker_lock(folder):
    path=folder/'worker.lock'
    no_links(path) if path.exists() else no_links(folder)
    with path.open('a+b') as stream:
        if stream.tell()==0: stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try: yield
        finally:
            stream.seek(0)
            if os.name=='nt': msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def prepare_job(job,mask,desktop,library,clock=time.time):
    no_links(WORKSPACE/'out');EXCHANGE.mkdir(exist_ok=True);no_links(EXCHANGE)
    if not re.fullmatch('[0-9a-f]{64}',job): raise SafetyError('invalid GUI job ID')
    folder=EXCHANGE/job;folder.mkdir(exist_ok=False)
    request=request_for(mask,desktop,library)
    meta=dict(job=job,binding=f'{mask}|{desktop}|{library}',created=clock())
    try:result=bridge.prepare(request)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        if REAL_ALLOWED!='1':raise
        result=dict(status='Blocked',profile=bridge.PROFILE,bridge_id='',summary='Game folder validation failed: '+str(exc),errors=[str(exc)])
    if result.get('profile'):meta['profile']=result['profile']
    meta.update(bridge_id=result['bridge_id'],plan_digest=result.get('plan_digest',''),prepared=result)
    exclusive_bytes(folder/'job.json',canonical(meta))
    if result['status']!='PreparedAwaitingConsent':
        publish(folder,meta,'Blocked',[result['summary'],str(result['errors'])],True)
        return meta
    title=('EXACT GAME INSTALLATION PLAN - not yet authorized' if REAL_ALLOWED=='1' else
           'EXACT REAL-FILE FIXTURE PLAN - not yet authorized' if meta.get('profile') else 'EXACT SYNTHETIC PLAN - not yet authorized')
    lines=[title,result['synthetic_root'],'']
    for row in result['operations']:
        lines += [row['action']+': '+row['path'],
                  'Before SHA-256: '+(row['before']['sha256'] if row['before'] else '(absent)'),
                  'After SHA-256: '+(row['after']['sha256'] if row['after'] else '(preserved unchanged)')]
    lines+=['','Plan: '+meta['plan_digest'],('Start requires explicit consent to modify the selected game directory using this exact plan.' if REAL_ALLOWED=='1' else 'Start requires a separate confirmation. No game files will be touched.')]
    if meta.get('profile'):lines=pack_lines(lines)
    publish(folder,meta,'Prepared',lines)
    return meta


def pack_lines(lines):
    # Preserve every path/hash/result without increasing the bounded v1 frame size.
    while len(lines)>40:
        lines=[' | '.join(lines[i:i+2]) for i in range(0,len(lines),2)]
    if any(len(line)>2000 for line in lines):raise SafetyError('real plan too large for bounded GUI transport')
    return lines


def finish(folder,meta,result):
    if meta.get('profile')=='real-component-fixture-v1':
        result['summary']='Real component files verified in a disposable fixture; no game installation or binary execution.'
    success=result['status']=='CommittedSynthetic'
    state='Completed' if success else ('RecoveryRequired' if result['status']=='RecoveryRequired' else 'Failed')
    lines=[result['summary'],'Status: '+result['status'],'Transaction: '+str(result.get('transaction_id') or '(none)'),
           'Backups verified: '+str(result.get('backups_verified',False))]
    lines += [r['action']+': '+r['path'] for r in result.get('completed_operations',[])]
    lines += ['Error: '+str(e) for e in result.get('errors',[])][:12]
    recovery_command=('HFBackend.exe install recover --id ' if getattr(sys,'frozen',False) else 'synthetic_install.py recover --id ')
    if REAL_ALLOWED=='1':recovery_command='HFBackend.exe private-gui recover --job '
    lines += ['Bridge: '+meta['bridge_id'],'Recovery: '+recovery_command+(meta['job'] if REAL_ALLOWED=='1' else meta['bridge_id'])]
    exclusive_bytes(folder/(str(uuid.uuid4())+'-result.json'),canonical(result))
    if meta.get('profile'):lines=pack_lines(lines)
    publish(folder,{**meta,'ui_result':result},state,lines,True,success)
    return result


def run_job(job,approved_plan,recover=False,clock=time.time,extra_fault=lambda point,index:None):
    folder=folder_for(job);meta=read_json(folder/'job.json')
    if meta['job']!=job: raise SafetyError('job identity mismatch')
    with worker_lock(folder):
        if not recover:
            if not approved_plan or approved_plan!=meta['plan_digest']: raise SafetyError('explicit matching consent required')
            if clock()<meta['created'] or clock()-meta['created']>600: raise SafetyError('plan approval window expired; prepare again')
            exclusive_bytes(folder/'execution.claim',canonical({'job':job,'approved_plan':approved_plan}))
        publish(folder,meta,'Validating',['Revalidating consent, source hashes and ownership.'])
        applied=set()
        def progress(point,index):
            if point in ('before_backup','after_backup_copy','before_backup_gate'): state='BackingUp'
            elif point in ('after_backup','after_intent','after_publish','after_applied'): state='Applying'
            elif point in ('after_files','registry_after_pending','registry_after_replace','after_registry','before_completion_ack','after_completion_ack'): state='Verifying'
            else: state='Validating'
            path=meta['prepared']['operations'][index]['path'] if index is not None and index < len(meta['prepared']['operations']) else '(transaction)'
            if point=='after_applied':applied.add(index)
            publish(folder,{**meta,'ui_applied':len(applied)},state,[state+': '+path,'Journal event boundary: '+point])
            extra_fault(point,index)
        try:
            if recover: result=bridge.recover(meta['bridge_id'])
            else: result=bridge.execute(meta['bridge_id'],approved_plan,fault=progress)
            return finish(folder,meta,result)
        except Exception as exc:
            # Never force a rollback after an uncertain ownership publication.
            publish(folder,meta,'RecoveryRequired',['No successful terminal acknowledgement: '+str(exc),
                     'Bridge: '+meta['bridge_id'],'Keep records. After the worker exits, use recover mode.'],True)
            return {'status':'RefusedUncertain','error':str(exc),'real_installation_allowed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    prep=commands.add_parser('prepare');prep.add_argument('--mask',type=int,required=True)
    prep.add_argument('--desktop',required=True);prep.add_argument('--library',required=True)
    for name in ('prepare','run','recover'):
        p=prep if name=='prepare' else commands.add_parser(name)
        p.add_argument('--job',required=True)
        if name=='run':p.add_argument('--approve-plan',required=True)
    args=parser.parse_args()
    try:
        if args.action=='prepare': prepare_job(args.job,args.mask,args.desktop,args.library)
        else: run_job(args.job,getattr(args,'approve_plan',None),recover=args.action=='recover')
        return 0
    except Exception as exc:
        # If execution has not been claimed, report refusal without altering another worker's frame.
        try:
            folder=folder_for(args.job);meta=read_json(folder/'job.json')
            if not (folder/'execution.claim').exists():
                publish(folder,meta,'Failed',['Backend refused: '+str(exc)],True)
        except Exception: pass
        print(str(exc),file=sys.stderr);return 3


if __name__=='__main__': sys.exit(main())
