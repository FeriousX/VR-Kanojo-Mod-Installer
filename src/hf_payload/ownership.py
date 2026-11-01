"""Synthetic receipt trust, lineage and consent. Never executes file operations."""
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import time
from .planner import build_plan, identity, expected
from .recovery import SyntheticArea, checked_area, SafetyError, canonical, digest, shape
from .validator import safe_relative, HASH


@dataclass(frozen=True)
class TrustPolicy:
    # Pins must arrive from an independent trusted channel, never from receipt metadata.
    pins: frozenset
    heads: frozenset = frozenset()

    def __post_init__(self):
        if not isinstance(self.pins, frozenset) or len(self.pins) > 1000 or any(
                not isinstance(p, str) or not HASH.fullmatch(p) for p in self.pins):
            raise SafetyError('invalid independent receipt pins')
        if not isinstance(self.heads, frozenset) or not self.heads <= self.pins:
            raise SafetyError('current heads must be independently pinned')

    @property
    def sha256(self):
        return digest({'pins': sorted(self.pins), 'heads': sorted(self.heads)})


def inventory(area, receipts, policy):
    """Return ownership classifications; malformed lineage always fails closed."""
    area = checked_area(area)
    if not isinstance(receipts, list) or len(receipts) > 1000:
        raise SafetyError('invalid receipt collection')
    nodes, installs, children = {}, set(), {}
    for r in receipts:
        shape(r, 'schema installation owner area target_id parent files')
        if type(r['schema']) is not int or r['schema'] != 1:
            raise SafetyError('unsupported receipt schema')
        identity(r['installation']); identity(r['owner'])
        if r['installation'] in installs:
            raise SafetyError('duplicate installation identity')
        installs.add(r['installation'])
        if r['area'] != area.path.name or r['target_id'] != area.marker['target_id']:
            raise SafetyError('receipt target identity mismatch')
        if r['parent'] is not None and (not isinstance(r['parent'], str) or not HASH.fullmatch(r['parent'])):
            raise SafetyError('invalid parent digest')
        # An empty complete snapshot retires the last owned file without erasing lineage.
        if not isinstance(r['files'], list) or not 0 <= len(r['files']) <= 1000:
            raise SafetyError('invalid owned files')
        seen = set()
        for f in r['files']:
            shape(f, 'path expected')
            path = safe_relative(f['path']).casefold()
            if any(path == p or path.startswith(p + '/') or p.startswith(path + '/') for p in seen):
                raise SafetyError('receipt path collision')
            seen.add(path); expected(f['expected'])
        sha = digest(r)
        nodes[sha] = r
        if r['parent'] is not None:
            children.setdefault(r['parent'], []).append(sha)
    if not policy.heads <= nodes.keys() or any(head in children for head in policy.heads):
        raise SafetyError('missing or superseded trusted current head')
    for sha, r in nodes.items():
        parent = r['parent']
        if parent is not None:
            if parent not in nodes or nodes[parent]['owner'] != r['owner']:
                raise SafetyError('missing or incompatible lineage parent')
        chain, cursor = set(), sha
        while cursor is not None:
            if cursor in chain:
                raise SafetyError('cyclic installation lineage')
            chain.add(cursor); cursor = nodes[cursor]['parent']
    files = {}
    for sha, r in nodes.items():
        if sha in children:  # descendants carry complete current ownership, not deltas
            continue
        trusted, forked, cursor = sha in policy.heads, False, sha
        while cursor is not None:
            trusted &= cursor in policy.pins
            parent = nodes[cursor]['parent']
            forked |= parent is not None and len(children[parent]) > 1
            cursor = parent
        for f in r['files']:
            files.setdefault(safe_relative(f['path']).casefold(), []).append({
                'owner': r['owner'], 'installation': r['installation'], 'receipt': sha,
                'expected': expected(f['expected']), 'trusted': trusted, 'forked': forked})
    result = {}
    for path, claims in files.items():
        owners = [c['owner'] for c in claims]
        if any(c['forked'] for c in claims) or len(set(owners)) != len(owners) or len({digest(c['expected']) for c in claims}) != 1:
            status = 'conflicting'
        elif not all(c['trusted'] for c in claims):
            status = 'unverified'
        else:
            status = 'shared' if len(claims) > 1 else 'verified'
        result[path] = {'status': status, 'claims': claims}
    return result


@dataclass(frozen=True)
class ReviewedPlan:
    document: str

    @property
    def sha256(self):
        return hashlib.sha256(self.document.encode()).hexdigest()

    def as_dict(self):
        return json.loads(self.document)


def review(area, requests, receipts, approvals, gates, policy):
    """Rebuild Phase 3C.1 plan using only independently pinned exclusive ownership."""
    ownership = inventory(area, receipts, policy)
    legacy = []
    for row in requests:
        path = safe_relative(row['destination']).casefold()
        record = ownership.get(path)
        if row['action'] == 'create' and record is not None:
            raise SafetyError('create collides with an existing ownership claim')
        if row['action'] in ('replace', 'delete'):
            if record is None or record['status'] != 'verified':
                raise SafetyError('destructive operation requires verified exclusive ownership')
            claim = record['claims'][0]
            legacy.append({'destination': row['destination'], 'owner': claim['owner'],
                           'expected': claim['expected'], 'receipt': 'pinned-' + claim['receipt'][:32]})
    plan = build_plan(area, requests, legacy, approvals, gates)
    return ReviewedPlan(canonical({'schema': 1, 'plan': plan.as_dict(), 'requests': requests,
                                   'receipts': receipts, 'approvals': approvals, 'gates': gates,
                                   'ownership': ownership, 'policy': policy.sha256}).decode())


class ConsentAuthority:
    """Ephemeral in-process synthetic consent issuer; no persistent security boundary."""
    def __init__(self, clock=time.time):
        self._key = secrets.token_bytes(32)
        self._clock = clock

    def _now(self):
        now = self._clock()
        if not isinstance(now, (int, float)) or not 0 <= now < 10**12:
            raise SafetyError('invalid clock')
        return now

    def issue(self, plan, approved_digest, ttl=300):
        if approved_digest != plan.sha256 or type(ttl) is not int or not 1 <= ttl <= 600:
            raise SafetyError('explicit full-plan approval or valid expiry missing')
        now = self._now()
        payload = {'plan': plan.sha256, 'issued': now, 'expires': now + ttl, 'nonce': secrets.token_hex(16)}
        return {'payload': payload, 'mac': hmac.new(self._key, canonical(payload), hashlib.sha256).hexdigest()}

    def validate(self, token, plan):
        shape(token, 'payload mac'); shape(token['payload'], 'plan issued expires nonce')
        body = token['payload']
        if not isinstance(token['mac'], str) or not hmac.compare_digest(
                token['mac'], hmac.new(self._key, canonical(body), hashlib.sha256).hexdigest()):
            raise SafetyError('unverified consent')
        now = self._now()
        if body['plan'] != plan.sha256 or not body['issued'] <= now < body['expires']:
            raise SafetyError('expired, future or changed-plan consent')

    def revalidate(self, area, plan, token, policy):
        """Immediate read-only handoff check. Returns no file executor/capability."""
        self.validate(token, plan)
        data = plan.as_dict()
        rebuilt = review(area, data['requests'], data['receipts'], data['approvals'], data['gates'], policy)
        if rebuilt.document != plan.document:
            raise SafetyError('plan, ownership, policy or file state changed; re-review required')
        self.validate(token, rebuilt)  # also catch expiry while scanning
        return {'synthetic_checks_passed': True, 'plan': plan.sha256,
                'installation_allowed': False, 'execution_authorized': False}
