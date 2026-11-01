"""Pinned compatibility policy with legacy exact-target recovery support; not version/authenticity proof."""
from dataclasses import dataclass
import json,sys
from pathlib import Path
from .recovery import SafetyError,digest,file_id,read_json
from .validator import no_links,stable_hash,safe_relative

@dataclass(frozen=True)
class PrivatePermit:
    document: str
    trusted_digest: str

    def policy(self):
        p=json.loads(self.document)
        if digest(p)!=self.trusted_digest or p.get('schema')!=1 or p.get('scope') not in ('private-disposable-game-test', 'compatible-original-game-v1'):
            raise SafetyError('private target policy pin mismatch')
        return p

    def check(self,profile,full=False):
        p=self.policy()
        if p['scope']=='compatible-original-game-v1':
            from .external_root import qualify_private_copy
            fresh=qualify_private_copy(profile['root'],selected_manually=True,
                protected_roots=p['protected_roots'],desktop=profile['desktop'],compatibility=True)
            if fresh!=profile:raise SafetyError('selected game changed since plan preparation; prepare a new plan')
            return p
        if (profile['root']!=p['target'] or profile['root_id']!=p['target_id'] or profile['files']!=p['files']
                or profile['layout']!=p['layout']):raise SafetyError('target is not the individually approved disposable copy')
        root=Path(p['target']);no_links(root)
        if file_id(root)!=p['target_id']:raise SafetyError('approved target identity changed')
        if full:
            for row in p.get('dependencies',[]):
                path=root/safe_relative(row['path'])
                if file_id(path)!=row['file_id'] or stable_hash(path)!=(row['size'],row['sha256']):
                    raise SafetyError('required game dependency changed: '+row['path'])
        return p


def load_permit():
    if getattr(sys,'frozen',False):
        from private_target_pin import POLICY_DIGEST
        p=read_json(Path(sys.executable).parent/'PrivateTarget.json');pin=POLICY_DIGEST
    else:
        w=Path(__file__).resolve().parents[2]
        p=read_json(w/'manifests/private-game-policy.json')
        pin=read_json(w/'manifests/private-game-policy.review.json')['policy_digest']
    permit=PrivatePermit(json.dumps(p),pin);permit.policy();return permit
