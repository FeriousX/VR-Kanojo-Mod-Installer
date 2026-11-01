"""One-shot synthetic transaction integration. Not a production installation API."""
import hashlib
import hmac
import uuid
from .ownership import ReviewedPlan
from .planner import Plan
from .registry import mac
from .recovery import (SyntheticArea, checked_area, Transaction, SafetyError, canonical, digest, shape,
                       read_json, exclusive_bytes, present, snapshot)
from .validator import safe_relative


class Coordinator:
    def __init__(self, area, registry, test_key):
        self.area = checked_area(area)
        if registry.area.path != self.area.path:
            raise SafetyError('registry and designated synthetic root differ')
        if not isinstance(test_key, bytes) or len(test_key) < 32 or test_key in (registry.key, registry.anchor_key):
            raise SafetyError('independent trusted synthetic authorization key required')
        self.registry, self.test_key = registry, test_key
        self.intent = self.area.path / 'coordinator-intent.json'

    def _context(self, plan, context_id):
        s = self.registry._current()
        self.registry._rebuild(s, plan)
        d = plan.as_dict()
        requests = d['requests']
        owners = {r['owner'] for r in requests if r['action'] != 'preserve'}
        if len(owners) != 1:
            raise SafetyError('one mutating installation owner per synthetic transaction required')
        owner = next(iter(owners))
        heads = [r for r in s['receipts'] if digest(r) in s['heads'] and r['owner'] == owner]
        if len(heads) > 1: raise SafetyError('ambiguous owner lineage')
        previous = heads[0] if heads else None
        files = {safe_relative(f['path']).casefold(): f for f in previous['files']} if previous else {}
        for r in requests:
            if r['action'] == 'preserve': continue
            key = safe_relative(r['destination']).casefold()
            if r['action'] == 'delete': files.pop(key, None)
            else: files[key] = {'path': safe_relative(r['destination']), 'expected': r['after']}
        receipt = dict(schema=1, installation=context_id, owner=owner, area=self.area.path.name,
                       target_id=self.area.marker['target_id'], parent=digest(previous) if previous else None,
                       files=[files[k] for k in sorted(files)])
        return {'scope': 'synthetic-transaction-only', 'id': context_id, 'area': self.area.path.name,
                'target_id': self.area.marker['target_id'], 'base': self.registry.stamp(s),
                'plan': plan.sha256, 'receipt': receipt}

    def authorize(self, plan, approved_digest):
        """Trusted test approver stand-in. No real compatibility or payload approval implied."""
        if plan.sha256 != approved_digest: raise SafetyError('explicit test plan approval missing')
        body = self._context(plan, str(uuid.uuid4()))
        return {'body': body, 'mac': mac(self.test_key, body)}

    def _verify_context(self, plan, context):
        shape(context, 'body mac')
        b = context['body']
        shape(b, 'scope id area target_id base plan receipt')
        if (not isinstance(context['mac'], str) or not hmac.compare_digest(context['mac'], mac(self.test_key, b))
                or str(uuid.UUID(b['id'])) != b['id'] or self._context(plan, b['id']) != b):
            raise SafetyError('untrusted, stale or wrong-root test authorization')

    def _write_signed(self, path, body):
        exclusive_bytes(path, canonical({'body': body, 'sha256': digest(body), 'mac': mac(self.registry.key, body)}))
        if self._read_signed(path) != body:
            raise SafetyError('coordinator acknowledgement readback failed')

    def _read_signed(self, path):
        value = read_json(path)
        shape(value, 'body sha256 mac')
        body = value['body']
        if value['sha256'] != digest(body) or not isinstance(value['mac'], str) or not hmac.compare_digest(value['mac'], mac(self.registry.key, body)):
            raise SafetyError('coordinator record integrity failure; manual review required')
        return body

    def _consumption_ack(self, intent, checkpoint):
        body = {'schema': 1, 'intent': digest(intent), 'base': self.registry.stamp(intent['registry_before']),
                'checkpoint': checkpoint, 'nonce': intent['nonce']}
        path = self.area.path / 'coordinator-consumed.json'
        if present(path):
            if self._read_signed(path) != body: raise SafetyError('conflicting consumption acknowledgement')
        else: self._write_signed(path, body)

    def _completion_ack(self, intent, tx):
        self._verify_results(tx)
        records, _ = tx.journal.read()
        body = {'schema': 1, 'intent': digest(intent), 'txid': tx.txid,
                'checkpoint': dict(self.registry.checkpoint), 'journal_tip': records[-1]['hash'],
                'backup_manifest': digest(tx.verify()), 'receipt': digest(intent['context']['body']['receipt'])}
        path = self.area.path / 'coordinator-completed.json'
        if present(path):
            if self._read_signed(path) != body: raise SafetyError('conflicting completion acknowledgement')
        else: self._write_signed(path, body)

    def resume(self, checkpoint, fault=lambda point, index: None):
        """Use a signed synthetic consumption acknowledgement to bridge this known revision.

        Local acknowledgements are not protected external rollback anchors.
        """
        intent = self._read_intent()
        base = self.registry.stamp(intent['registry_before'])
        ack_path = self.area.path / 'coordinator-consumed.json'
        if present(ack_path):
            ack = self._read_signed(ack_path)
            shape(ack, 'schema intent base checkpoint nonce')
            if (ack['schema'] != 1 or ack['intent'] != digest(intent) or ack['base'] != base
                    or ack['nonce'] != intent['nonce'] or ack['checkpoint']['revision'] != base['revision'] + 1):
                raise SafetyError('invalid consumption checkpoint bridge')
            if checkpoint == base: checkpoint = ack['checkpoint']
        self.registry.open(checkpoint)
        state = self.registry._current()
        # A crash immediately after spending consent may precede the ack write.
        if not present(ack_path) and intent['nonce'] in state['consumed']:
            if (state['previous'] != base['sha256'] or state['revision'] != base['revision'] + 1
                    or state['receipts'] != intent['registry_before']['receipts']):
                raise SafetyError('unacknowledged registry transition is uncertain')
            self._consumption_ack(intent, self.registry.stamp(state))
        return self.recover(fault=fault)

    def _read_intent(self):
        checked_area(self.area)
        value = read_json(self.intent)
        shape(value, 'body sha256 mac')
        b = value['body']
        if value['sha256'] != digest(b) or not isinstance(value['mac'], str) or not hmac.compare_digest(value['mac'], mac(self.registry.key, b)):
            raise SafetyError('coordinator intent integrity failure')
        shape(b, 'schema area target_id plan context nonce registry_before operations')
        if b['schema'] != 1 or b['area'] != self.area.path.name or b['target_id'] != self.area.marker['target_id']:
            raise SafetyError('coordinator intent root mismatch')
        context = b['context']; shape(context, 'body mac')
        if not isinstance(context['mac'], str) or not hmac.compare_digest(context['mac'], mac(self.test_key, context['body'])):
            raise SafetyError('test context cannot be authenticated on restart')
        plan = ReviewedPlan(b['plan'])
        if context['body']['plan'] != plan.sha256 or self._operations(plan) != b['operations']:
            raise SafetyError('intent/plan binding mismatch')
        return b

    @staticmethod
    def _operations(plan):
        return Plan(canonical(plan.as_dict()['plan']).decode()).recovery_operations()

    def _session(self, intent):
        sessions = list(self.area.sessions.iterdir())
        if len(sessions) > 1: raise SafetyError('unexpected additional transactions')
        if not sessions: return None
        tx = Transaction(self.area, sessions[0].name)
        manifest = tx.verify()
        if manifest['plan'] != intent['operations']:
            raise SafetyError('backup session belongs to a different operation plan')
        reviewed = ReviewedPlan(intent['plan']).as_dict()['plan']['operations']
        if manifest['before'] != [r['before'] for r in reviewed]:
            raise SafetyError('backup preimages differ from authorized review')
        return tx

    def _verify_results(self, tx):
        manifest = tx.verify()
        if tx.inspect()['state'] != 'Completed': raise SafetyError('file transaction is not completed')
        records, _ = tx.journal.read()
        applied = {r['data']['op']: r['data']['post'] for r in records if r['event'] == 'APPLIED'}
        for i, op in enumerate(manifest['plan']):
            expected = manifest['before'][i] if op['action'] == 'protect' else applied[i]
            if snapshot(self.area.destination(op['path'])) != expected:
                raise SafetyError('results changed before ownership commit')

    def execute(self, plan, consent, context, fault=lambda point, index: None):
        checked_area(self.area)
        if present(self.intent) or any(self.area.sessions.iterdir()):
            raise SafetyError('one execution per synthetic area; inspect/recover instead of replay')
        self._verify_context(plan, context)
        initial = self.registry._current()
        # Consent itself is validated durably by Registry.consume before backup/apply.
        intent = {'schema': 1, 'area': self.area.path.name, 'target_id': self.area.marker['target_id'],
                  'plan': plan.document, 'context': context, 'nonce': consent['body']['nonce'],
                  'registry_before': initial, 'operations': self._operations(plan)}
        self._write_signed(self.intent, intent)  # exclusive durable one-shot/restart binding
        try:
            consumed = self.registry.consume(plan, consent)
            checkpoint = consumed['checkpoint']
            fault('before_consumption_ack', None)
            self._consumption_ack(intent, checkpoint)
            fault('after_consumption_ack', None)
            fault('after_consent', None)
            self.area.prepare_directories(plan, fault)
            postimages = {}
            for r in plan.as_dict()['plan']['operations']:
                if r['action'] in ('create', 'replace'):
                    source = self.area.path / 'payload' / r['source']
                    if snapshot(source) != r['source_state']: raise SafetyError('source changed after consent')
                    data = source.read_bytes()
                    if len(data) != r['post']['size'] or hashlib.sha256(data).hexdigest() != r['post']['sha256']:
                        raise SafetyError('source bytes mismatch')
                    postimages[r['destination']] = data
            if self.registry.stamp(self.registry._current()) != checkpoint:
                raise SafetyError('registry changed before backup')
            tx = self.area.prepare(intent['operations'], fault)
            self._session(intent).verify()
            fault('after_backup', None)
            def apply_fault(point, index):
                if self.registry.stamp(self.registry._current()) != checkpoint:
                    raise SafetyError('registry changed before mutation')
                fault(point, index)
            tx.simulate_apply(postimages, apply_fault)
            self._verify_results(tx)
            fault('after_files', None)
            self._verify_results(tx)
            receipt = context['body']['receipt']
            receipts = initial['receipts'] + [receipt]
            heads = (set(initial['heads']) - {receipt['parent']}) | {digest(receipt)}
            req = self.registry.anchor_request(receipts, {digest(r) for r in receipts}, heads)
            if req['base'] != checkpoint: raise SafetyError('registry changed before ownership commit')
            authorization = self.registry.approve_anchor(req, digest(req))
            self.registry.update_trust(req, authorization, lambda point: fault('registry_' + point, None))
            fault('after_registry', None)
            self._verify_results(tx)
            fault('before_completion_ack', None)
            self._completion_ack(intent, tx)
            fault('after_completion_ack', None)
            return {'status': 'CommittedSynthetic', 'txid': tx.txid, 'plan': plan.sha256,
                    'checkpoint': dict(self.registry.checkpoint), 'installation_allowed': False}
        except Exception as exc:
            # Registry publication may have succeeded even if its acknowledgement failed.
            self._write_signed(self.area.path / ('coordinator-error-' + str(uuid.uuid4()) + '.json'),
                               {'type': type(exc).__name__, 'message': str(exc)[:2048]})
            return self.recover()

    def recover(self, fault=lambda point, index: None):
        intent = self._read_intent()
        # Reconcile a pending immediate registry successor; caller retains returned checkpoints.
        self.registry.open(self.registry.checkpoint)
        state = self.registry._current()
        expected = intent['context']['body']['receipt']
        committed = any(digest(r) == digest(expected) for r in state['receipts'])
        tx = self._session(intent)
        if tx is not None and intent['nonce'] not in state['consumed']:
            raise SafetyError('transaction lacks durable consent consumption')
        if committed:
            if tx is None: raise SafetyError('ownership committed without a verified transaction')
            self._verify_results(tx)  # never roll back already committed ownership
            self._completion_ack(intent, tx)
            return {'status': 'CommittedSynthetic', 'txid': tx.txid, 'checkpoint': dict(self.registry.checkpoint), 'installation_allowed': False}
        old = intent['registry_before']
        if (state['receipts'], state['pins'], state['heads'], state['trust_version']) != (old['receipts'], old['pins'], old['heads'], old['trust_version']):
            raise SafetyError('ownership changed externally; automatic recovery refused')
        if tx is None:
            return {'status': 'AbortedNoTargetWrites', 'checkpoint': dict(self.registry.checkpoint), 'installation_allowed': False}
        recovered = tx.recover(fault=fault)
        return {'status': recovered['state'], 'txid': tx.txid, 'checkpoint': dict(self.registry.checkpoint), 'installation_allowed': False}
