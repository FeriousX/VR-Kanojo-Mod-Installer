"""Root-bound external transaction adapter; target policy controls enrollment.

Local HMAC/checkpoints require independently retained caller keys; neither is vendor
proof. Fixture enrollment stays isolated; compatible-game enrollment requires a checked policy and plan consent.
"""
import hashlib
import hmac
import os
import sys
from pathlib import Path
import threading
import uuid
from contextlib import contextmanager
from .recovery import (SyntheticArea, SafetyError, WORKSPACE, canonical, digest,
                       file_id, read_json, exclusive_bytes, present, snapshot, safe_existing)
from .validator import no_links, safe_relative
from .detection import detect, desktop_compatibility
from .coordinator import Coordinator

STATE_ROOT = WORKSPACE / 'out' / 'external-transactions'
FIXTURE_ROOT = WORKSPACE / 'out' / 'external-game-fixtures'


def qualify_private_copy(raw_root, *, selected_manually=False, disposable_confirmed=False,
                         protected_roots=None, desktop='neither', compatibility=False):
    """Read-only private fingerprint, NOT v1.31/API/provenance certification."""
    if not selected_manually or (not compatibility and not disposable_confirmed):
        raise SafetyError('manual selection and disposable-copy acknowledgement required')
    if type(raw_root) is not str or raw_root != raw_root.strip() or any(c in raw_root for c in '\0\r\n"'):
        raise SafetyError('invalid target path')
    root = Path(os.path.abspath(raw_root))
    if not Path(raw_root).is_absolute() or root.parent == root or raw_root.startswith(('\\\\','//')):
        raise SafetyError('absolute local non-root directory required')
    if protected_roots is None or (not compatibility and any(p.casefold() == 'steamapps' for p in root.parts)):
        raise SafetyError('explicit protected-root policy required; Steam-library paths forbidden')
    for value in protected_roots:
        p = Path(value)
        if not p.is_absolute(): raise SafetyError('protected roots must be absolute')
        p = Path(os.path.abspath(p))
        if root == p or root in p.parents or p in root.parents:
            raise SafetyError('target overlaps protected root; not inspected')
    no_links(root)
    result = detect(root)
    if result['status'] != 'recognized-unverified' or result.get('unity_version_hint') != '5.4.5p1':
        raise SafetyError('Unqualified game structure/engine (expected x64 Unity 5.4.5p1): ' + result['validation_message'] + ' ' + '; '.join(result['reasons']))
    if 'VRKanojo' not in ''.join(result.get('app_info_hint', [])):
        raise SafetyError('unrecognized application identity evidence')
    dependencies=[]
    if compatibility:
        if not any(line.strip().casefold()=='vrkanojo' for line in result.get('app_info_hint',[])):
            raise SafetyError('Original VR Kanojo application identity required; directory names alone are insufficient')
        for reserved in ((WORKSPACE, Path(sys.executable).parent) if getattr(sys,'frozen',False) else ()):
            if root==reserved or root in reserved.parents or reserved in root.parents:
                raise SafetyError('Game folder overlaps installer runtime/state; select a separate game directory')
        from .game_compatibility import dependency_evidence
        dependencies=dependency_evidence(root,result['layout']['data'])
    conflicts = desktop_compatibility(result, desktop)['blockers']
    if conflicts: raise SafetyError('; '.join(conflicts))
    profile=dict(schema=1, scope='private-disposable-local-fingerprint', root=str(root),
                root_id=file_id(root), layout=result['layout'], files=result['files'],
                game_version=None, version_confidence='unverified', unity_hint=result['unity_version_hint'],
                desktop=desktop, protected_roots=[str(Path(os.path.abspath(p))) for p in protected_roots],
                production_writes_allowed=False)
    if compatibility:profile['dependencies']=dependencies
    return profile


def _mac(key, body):
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


class ExternalArea(SyntheticArea):
    manifest_kind = 'external-fixture-basic-v1'

    @classmethod
    def enroll_fixture(cls, profile, reviewed_digest, key):
        if digest(profile) != reviewed_digest: raise SafetyError('explicit exact-profile review required')
        root = Path(profile['root'])
        # No real-game execution capability is issued by this milestone.
        if root.parent != FIXTURE_ROOT: raise SafetyError('production enrollment disabled; dedicated fixtures only')
        uuid.UUID(root.name)
        if type(key) is not bytes or len(key) < 32: raise SafetyError('external capability key required')
        fresh = qualify_private_copy(str(root), selected_manually=True, disposable_confirmed=True,
                   protected_roots=profile['protected_roots'], desktop=profile['desktop'])
        if fresh != profile: raise SafetyError('profile changed before enrollment')
        STATE_ROOT.mkdir(exist_ok=True)
        no_links(STATE_ROOT)
        path = STATE_ROOT / str(uuid.uuid4()); path.mkdir()
        (path / 'sessions').mkdir(); (path / 'payload').mkdir()
        body = dict(schema=1, id=path.name, root_id=file_id(path), target_id=file_id(root),
                    sessions_id=file_id(path/'sessions'), profile=profile)
        exclusive_bytes(path/'external.json', canonical(dict(body=body, mac=_mac(key,body))))
        return cls(path,key,reviewed_digest)

    @classmethod
    def enroll_private(cls, profile, reviewed_digest, key, permit):
        from .private_target import PrivatePermit
        if type(permit) is not PrivatePermit or digest(profile)!=reviewed_digest:
            raise SafetyError('independent exact private profile approval required')
        permit.check(profile,full=True)
        if type(key) is not bytes or len(key)<32:raise SafetyError('private capability key required')
        fresh=qualify_private_copy(profile['root'],selected_manually=True,disposable_confirmed=True,
                  protected_roots=profile['protected_roots'],desktop=profile['desktop'],
                  compatibility=permit.policy()['scope']=='compatible-original-game-v1')
        if fresh!=profile:raise SafetyError('private profile changed before enrollment')
        STATE_ROOT.mkdir(exist_ok=True);no_links(STATE_ROOT)
        path=STATE_ROOT/str(uuid.uuid4());path.mkdir()
        (path/'sessions').mkdir();(path/'payload').mkdir()
        body=dict(schema=1,id=path.name,root_id=file_id(path),target_id=file_id(Path(profile['root'])),
                  sessions_id=file_id(path/'sessions'),profile=profile,private_policy=permit.trusted_digest)
        exclusive_bytes(path/'external.json',canonical(dict(body=body,mac=_mac(key,body))))
        return cls(path,key,reviewed_digest,permit)

    def __init__(self, path, key, profile_pin, permit=None):
        self.path = Path(os.path.abspath(path)); self.key=key; self.profile_pin=profile_pin
        self._local=threading.local(); self.permit=permit
        if type(key) is not bytes or len(key)<32: raise SafetyError('external key required')
        self.revalidate()

    def revalidate(self):
        if self.path.parent != STATE_ROOT: raise SafetyError('external state outside designated root')
        uuid.UUID(self.path.name); no_links(self.path)
        value=read_json(self.path/'external.json'); b=value['body']
        if not hmac.compare_digest(value['mac'],_mac(self.key,b)) or digest(b['profile'])!=self.profile_pin:
            raise SafetyError('external state/profile integrity failure')
        target=Path(b['profile']['root']); sessions=self.path/'sessions'
        if b.get('private_policy'):
            from .private_target import PrivatePermit
            if type(self.permit) is not PrivatePermit or b['private_policy']!=self.permit.trusted_digest:
                raise SafetyError('private target requires its separately pinned policy')
            self.permit.check(b['profile'])
            self.manifest_kind='private-disposable-basic-v1'
        elif target.parent!=FIXTURE_ROOT: raise SafetyError('production target disabled')
        no_links(target);no_links(sessions)
        if b['id']!=self.path.name or b['root_id']!=file_id(self.path) or b['target_id']!=file_id(target) or b['sessions_id']!=file_id(sessions):
            raise SafetyError('external root identity changed')
        if file_id(target)[0]!=file_id(sessions)[0]: raise SafetyError('target/state must share a volume')
        self.target,self.sessions,self.marker=target,sessions,b

    def verify_fingerprint(self):
        fresh=qualify_private_copy(str(self.target),selected_manually=True,disposable_confirmed=True,
                    protected_roots=self.marker['profile']['protected_roots'],desktop=self.marker['profile']['desktop'],
                    compatibility=bool(self.permit and self.permit.policy()['scope']=='compatible-original-game-v1'))
        if fresh!=self.marker['profile']: raise SafetyError('build fingerprint changed; new review required')
        if self.permit:self.permit.check(fresh,full=True)

    @contextmanager
    def lock(self):
        self.revalidate()
        if getattr(self._local,'depth',0):
            self._local.depth+=1
            try: yield
            finally: self._local.depth-=1
            return
        # All independently enrolled states for this same target use one lock file.
        folder=STATE_ROOT/'locks';folder.mkdir(exist_ok=True);no_links(folder)
        path=folder/(digest(dict(target_id=file_id(self.target)))+'.lock')
        if present(path):safe_existing(path)
        with path.open('a+b') as f:
            if f.tell()==0:f.write(b'0');f.flush()
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            self._local.depth=1
            try:yield
            finally:
                self._local.depth=0;f.seek(0)
                if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

    def destination(self, relative):
        current=self.target
        for part in safe_relative(relative).split('/'):
            if present(current):
                no_links(current)
                if not current.is_dir():raise SafetyError('destination ancestor is not a directory')
                aliases=[p.name for p in current.iterdir() if p.name.casefold()==part.casefold()]
                if aliases and aliases!=[part]:raise SafetyError('case-insensitive destination collision')
            current=current/part
        if present(current):no_links(current)
        return current

    def inspect_destination(self, relative):
        path=self.destination(relative)
        if not path.parent.exists():return {'exists':False}
        return snapshot(path)

    def _record(self,name,body):
        exclusive_bytes(self.path/name,canonical(dict(body=body,mac=_mac(self.key,body))))

    def _read(self,name):
        v=read_json(self.path/name)
        if not hmac.compare_digest(v['mac'],_mac(self.key,v['body'])):raise SafetyError('directory record integrity failure')
        return v['body']

    def prepare_directories(self, plan, fault):
        self.verify_fingerprint()
        dirs=set()
        for row in plan.as_dict()['plan']['operations']:
            if row['action'] not in ('create','replace'):continue
            parent=Path(row['destination']).parent
            while parent!=Path('.'):
                dirs.add(parent.as_posix());parent=parent.parent
        # Exact directories are derived from the consent-bound file plan, not UI paths.
        self._record('directories.json',dict(plan=plan.sha256,paths=sorted(dirs,key=lambda x:(x.count('/'),x))))
        for i,relative in enumerate(sorted(dirs,key=lambda x:(x.count('/'),x))):
            path=self.destination(relative)
            if present(path):
                if not path.is_dir():raise SafetyError('directory required')
                self._record('directory-%04d.json'%i,dict(path=relative,id=file_id(path),created=False))
                continue
            intent=dict(path=relative,parent=file_id(path.parent))
            self._record('mkdir-%04d.json'%i,intent)
            fault('before_directory_create',i)
            path.mkdir()
            fault('after_directory_create',i)
            self._record('directory-%04d.json'%i,dict(path=relative,id=file_id(path),created=True))
            fault('after_directory_ack',i)

    def verify_directories(self):
        if not present(self.path/'directories.json'):return []
        body=self._read('directories.json');created=[]
        intent=read_json(self.path/'coordinator-intent.json')['body']
        from .ownership import ReviewedPlan
        if ReviewedPlan(intent['plan']).sha256!=body['plan']:raise SafetyError('directory/consent plan differs')
        for i,relative in enumerate(body['paths']):
            ack=self.path/('directory-%04d.json'%i);pending=self.path/('mkdir-%04d.json'%i)
            target=self.destination(relative)
            if present(ack):
                row=self._read(ack.name)
                if row['path']!=relative or not target.is_dir() or row['id']!=file_id(target):raise SafetyError('recorded directory changed')
                if row['created']:created.append(relative)
            elif present(pending):
                row=self._read(pending.name)
                if row['path']!=relative or file_id(target.parent)!=row['parent'] or present(target):
                    raise SafetyError('uncertain directory creation; manual review required')
        return created


class ExternalCoordinator(Coordinator):
    """Full-target serialization; nested registry/backup locks remain reentrant."""
    def execute(self,*args,**kwargs):
        with self.area.lock():
            self.area.verify_fingerprint()
            plan=args[0] if args else kwargs['plan']
            protected={r['path'].casefold() for r in self.area.marker['profile']['files']}
            data=self.area.marker['profile']['layout']['data'].casefold()
            for row in plan.as_dict()['plan']['operations']:
                dest=row['destination'].casefold()
                if row['action']!='preserve' and (dest in protected or dest.startswith(data+'/')):
                    raise SafetyError('native game files are outside plugin-only transaction scope')
            return super().execute(*args,**kwargs)

    def recover(self,*args,**kwargs):
        with self.area.lock():
            directories=self.area.verify_directories()
            result=super().recover(*args,**kwargs)
            result['retained_created_directories']=directories
            if directories and result['status']=='AbortedNoTargetWrites':result['status']='AbortedFilesNotAppliedDirectoriesRetained'
            return result


def configuration_operation(existing, required):
    """Preserve all user settings. Required mismatches block; no blind INI overwrite."""
    import configparser
    def parse(data):
        if len(data)>65536 or b'\0' in data:raise SafetyError('unsafe configuration encoding/size')
        p=configparser.ConfigParser(interpolation=None,strict=True)
        try:p.read_string(data.decode('utf-8-sig'))
        except (UnicodeError,configparser.Error) as exc:raise SafetyError('invalid configuration: '+str(exc))
        return p
    wanted=parse(required)
    if existing is None:return 'create'
    current=parse(existing)
    for section in wanted.sections():
        for key,value in wanted.items(section):
            if not current.has_option(section,key) or current.get(section,key)!=value:
                raise SafetyError('required configuration differs; preserve file and require separately reviewed migration')
    return 'preserve'

def component_requests(area, selected, desktop):
    """Stage ONLY catalog-pinned payload bytes; never adopt unknown target ownership.

    Existing matching binaries/configuration are preserved. Different binaries block.
    Different required INI values block pending a separately reviewed migration.
    """
    import shutil
    from .real_file_bridge import load_catalog
    from .component_packages import select_runtime
    from .validator import stable_hash
    from .recovery import checked_area
    area=checked_area(area)
    if type(area) is not ExternalArea:raise SafetyError('external capability required')
    if desktop!=area.marker['profile']['desktop']:raise SafetyError('selection differs from qualified profile')
    area.verify_fingerprint()
    catalog,source=load_catalog();rows=select_runtime(catalog,selected,desktop);requests=[]
    for f in rows:
        original=source/f['staged_source'];no_links(original)
        if stable_hash(original)!=(f['size'],f['sha256']):raise SafetyError('component payload changed')
        destination=safe_relative(f['destination'])
        if destination.casefold() in {r['path'].casefold() for r in area.marker['profile']['files']}:
            raise SafetyError('component mapping overlaps protected game evidence')
        state=area.inspect_destination(destination)
        action='create'
        if state['exists']:
            if destination.casefold().endswith('.ini'):
                action=configuration_operation(area.destination(destination).read_bytes(),original.read_bytes())
            elif all(state[k]==f[k] for k in ('size','sha256')):action='preserve'
            else:raise SafetyError('unknown or changed existing component; preserved: '+destination)
        request=dict(destination=destination,source=None,action=action,owner='private-components',
                     before={k:state[k] for k in ('size','sha256')} if state['exists'] else None,after=None)
        if action=='create':
            target=area.path/'payload'/destination
            no_links(target.parent if target.parent.exists() else area.path/'payload')
            target.parent.mkdir(parents=True,exist_ok=True);no_links(target.parent)
            with target.open('xb') as out,original.open('rb') as inp:
                shutil.copyfileobj(inp,out);out.flush();os.fsync(out.fileno())
            if stable_hash(target)!=(f['size'],f['sha256']):raise SafetyError('staged component readback failed')
            request.update(source=destination,after={k:f[k] for k in ('size','sha256')})
        requests.append(request)
    return requests
