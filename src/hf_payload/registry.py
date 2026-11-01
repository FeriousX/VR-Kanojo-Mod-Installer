"""Persistent synthetic registry. External secrets/checkpoints are caller responsibilities."""
import hashlib
import hmac
import os
import secrets
import time
from .ownership import TrustPolicy, inventory, review
from .recovery import SyntheticArea, checked_area, SafetyError, canonical, digest, shape, read_json, exclusive_bytes, present
from .validator import HASH


def mac(key, value):
    return hmac.new(key, canonical(value), hashlib.sha256).hexdigest()


class Registry:
    def __init__(self, area, key, anchor_key, clock=time.time):
        self.area = checked_area(area)
        if any(not isinstance(k, bytes) or len(k) < 32 for k in (key, anchor_key)) or key == anchor_key:
            raise SafetyError('independent external registry and anchor keys required')
        self.key, self.anchor_key, self.clock = key, anchor_key, clock
        self.path = self.area.path / 'registry.json'
        self.pending = self.area.path / 'registry.pending'
        self.checkpoint = None

    def _now(self):
        value = self.clock()
        if type(value) not in (int, float) or not 0 <= value < 10**12:
            raise SafetyError('invalid clock')
        return value

    def _validate(self, s):
        shape(s, 'schema area target_id revision previous trust_version receipts pins heads consumed last_time')
        if (type(s['schema']) is not int or s['schema'] != 1 or s['area'] != self.area.path.name
                or s['target_id'] != self.area.marker['target_id']):
            raise SafetyError('wrong registry schema/root')
        if any(type(s[k]) is not int or s[k] < 0 for k in ('revision', 'trust_version')):
            raise SafetyError('invalid registry version')
        if s['revision'] == 0 and s['previous'] is not None:
            raise SafetyError('invalid initial lineage')
        if s['revision'] > 0 and (not isinstance(s['previous'], str) or len(s['previous']) != 64):
            raise SafetyError('invalid state predecessor')
        if type(s['last_time']) not in (int, float) or not 0 <= s['last_time'] < 10**12:
            raise SafetyError('invalid clock watermark')
        for name in ('pins', 'heads', 'consumed'):
            if not isinstance(s[name], list) or len(s[name]) != len(set(s[name])):
                raise SafetyError('duplicate registry records')
        if len(s['consumed']) > 10000 or any(not isinstance(x, str) or len(x) != 32 for x in s['consumed']):
            raise SafetyError('invalid/full replay ledger')
        policy = TrustPolicy(frozenset(s['pins']), frozenset(s['heads']))
        records = inventory(self.area, s['receipts'], policy)
        if any(r['status'] in ('conflicting', 'unverified') for r in records.values()):
            raise SafetyError('conflicting or untrusted registry ownership')
        if set(s['pins']) != {digest(r) for r in s['receipts']}:
            raise SafetyError('pins must bind the complete registered history')
        return s

    def _read(self, path):
        envelope = read_json(path)
        shape(envelope, 'state sha256 mac')
        state = envelope['state']
        if envelope['sha256'] != digest(state) or not isinstance(envelope['mac'], str) or not hmac.compare_digest(envelope['mac'], mac(self.key, state)):
            raise SafetyError('registry integrity/authenticator failure')
        return self._validate(state)

    @staticmethod
    def stamp(s):
        return {'revision': s['revision'], 'sha256': digest(s)}

    def _publish(self, state, fault=lambda _: None):
        self._validate(state)
        envelope = {'state': state, 'sha256': digest(state), 'mac': mac(self.key, state)}
        exclusive_bytes(self.pending, canonical(envelope))
        if self._read(self.pending) != state:
            raise SafetyError('pending readback mismatch')
        fault('after_pending')
        os.replace(self.pending, self.path)
        fault('after_replace')
        if self._read(self.path) != state:
            raise SafetyError('registry publication readback mismatch')
        self.checkpoint = self.stamp(state)
        return dict(self.checkpoint)

    def create(self):
        with self.area.lock():
            if present(self.path) or present(self.pending):
                raise SafetyError('registry already exists or interrupted creation needs review')
            state = dict(schema=1, area=self.area.path.name, target_id=self.area.marker['target_id'],
                         revision=0, previous=None, trust_version=0, receipts=[], pins=[], heads=[],
                         consumed=[], last_time=self._now())
            return self._publish(state)

    def open(self, checkpoint):
        """Requires separately retained checkpoint. Recover only a verified immediate successor."""
        shape(checkpoint, 'revision sha256')
        if (type(checkpoint['revision']) is not int or checkpoint['revision'] < 0
                or not isinstance(checkpoint['sha256'], str) or not HASH.fullmatch(checkpoint['sha256'])):
            raise SafetyError('invalid external checkpoint')
        with self.area.lock():
            current = self._read(self.path)
            if present(self.pending):
                pending = self._read(self.pending)
                if (self.stamp(current) != checkpoint or pending['revision'] != current['revision'] + 1
                        or pending['previous'] != digest(current)):
                    raise SafetyError('stale/conflicting pending registry; retain evidence')
                os.replace(self.pending, self.path)
                current = self._read(self.path)
            if self.stamp(current) != checkpoint and not (
                    current['revision'] == checkpoint['revision'] + 1 and current['previous'] == checkpoint['sha256']):
                raise SafetyError('stale/rolled-back registry or checkpoint')
            self.checkpoint = self.stamp(current)
            return dict(self.checkpoint)

    def _current(self):
        if self.checkpoint is None or present(self.pending):
            raise SafetyError('open/recover registry before use')
        checked_area(self.area)
        s = self._read(self.path)
        if self.stamp(s) != self.checkpoint:
            raise SafetyError('stale registry handle; refresh required')
        if self._now() < s['last_time']:
            raise SafetyError('clock precedes durable watermark')
        return s

    def anchor_request(self, receipts, pins, heads):
        with self.area.lock():
            s = self._current()
            return {'base': self.stamp(s), 'trust_version': s['trust_version'] + 1,
                    'receipts': receipts, 'pins': sorted(pins), 'heads': sorted(heads)}

    def approve_anchor(self, request, approved_digest):
        """Synthetic external approver stand-in; possession of anchor key is authority."""
        if digest(request) != approved_digest:
            raise SafetyError('explicit anchor-change approval missing')
        return mac(self.anchor_key, request)

    def update_trust(self, request, authorization, fault=lambda _: None):
        with self.area.lock():
            s = self._current()
            shape(request, 'base trust_version receipts pins heads')
            if not isinstance(authorization, str) or not hmac.compare_digest(authorization, mac(self.anchor_key, request)):
                raise SafetyError('unauthorized trust replacement')
            if request['base'] != self.stamp(s) or type(request['trust_version']) is not int or request['trust_version'] != s['trust_version'] + 1:
                raise SafetyError('stale or downgraded trust version')
            # No silent history rewrite/removal; every old immutable receipt remains.
            if not {digest(r) for r in s['receipts']} <= {digest(r) for r in request['receipts']}:
                raise SafetyError('receipt history removal/replacement forbidden')
            s.update({k: request[k] for k in ('trust_version', 'receipts', 'pins', 'heads')})
            s.update(previous=self.checkpoint['sha256'], revision=s['revision'] + 1, last_time=self._now())
            return self._publish(s, fault)

    @staticmethod
    def _policy(s):
        return TrustPolicy(frozenset(s['pins']), frozenset(s['heads']))

    def plan(self, requests, approvals, gates):
        with self.area.lock():
            s = self._current()
            plan = review(self.area, requests, s['receipts'], approvals, gates, self._policy(s))
            return plan

    def issue(self, plan, approved_digest, ttl=300):
        with self.area.lock():
            s = self._current()
            self._rebuild(s, plan)
            if plan.sha256 != approved_digest or type(ttl) is not int or not 1 <= ttl <= 600:
                raise SafetyError('full-plan approval or expiry missing')
            now = self._now()
            body = {'registry': self.stamp(s), 'trust_version': s['trust_version'], 'plan': plan.sha256,
                    'issued': now, 'expires': now + ttl, 'nonce': secrets.token_hex(16)}
            return {'body': body, 'mac': mac(self.key, body)}

    def _rebuild(self, s, plan):
        d = plan.as_dict()
        rebuilt = review(self.area, d['requests'], s['receipts'], d['approvals'], d['gates'], self._policy(s))
        if rebuilt.document != plan.document:
            raise SafetyError('changed plan, files, registry or trust; re-review required')

    def consume(self, plan, token, fault=lambda _: None):
        with self.area.lock():
            s = self._current()
            shape(token, 'body mac')
            b = token['body']
            shape(b, 'registry trust_version plan issued expires nonce')
            if not isinstance(token['mac'], str) or not hmac.compare_digest(token['mac'], mac(self.key, b)):
                raise SafetyError('unauthenticated consent')
            now = self._now()
            if (b['registry'] != self.stamp(s) or b['trust_version'] != s['trust_version'] or b['plan'] != plan.sha256
                    or not b['issued'] <= now < b['expires'] or b['nonce'] in s['consumed']):
                raise SafetyError('stale, expired or replayed consent')
            self._rebuild(s, plan)
            if not b['issued'] <= self._now() < b['expires']:
                raise SafetyError('consent expired during revalidation')
            s['consumed'].append(b['nonce'])
            s.update(previous=self.checkpoint['sha256'], revision=s['revision'] + 1, last_time=self._now())
            checkpoint = self._publish(s, fault)
            return {'consumed': True, 'checkpoint': checkpoint, 'installation_allowed': False, 'execution_authorized': False}
