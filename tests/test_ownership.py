import copy
import shutil
import unittest
from hf_payload import ownership as o
from hf_payload.planner import approval_key
from hf_payload.recovery import SyntheticArea, BASE, digest
from test_planner import spec


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.area = SyntheticArea.create()
        (self.area.path / 'payload').mkdir()
        (self.area.path / 'payload' / 'new.bin').write_bytes(b'new')
        (self.area.target / 'old.bin').write_bytes(b'old')
        self.row = dict(destination='old.bin', source='new.bin', action='replace', owner='package', before=spec(b'old'), after=spec(b'new'))
        self.receipt = dict(schema=1, installation='install-1', owner='package', area=self.area.path.name,
                            target_id=self.area.marker['target_id'], parent=None,
                            files=[{'path':'old.bin', 'expected':spec(b'old')}])
        self.receipts = [self.receipt]
        self.gates = dict(profile='synthetic', licensing=True, provenance=True, compatibility=True, mapping=True)
        self.policy = o.TrustPolicy(frozenset([digest(self.receipt)]), frozenset([digest(self.receipt)]))
        self.now = 1000
        self.auth = o.ConsentAuthority(clock=lambda: self.now)

    def tearDown(self):
        self.assertEqual(self.area.path.parent, BASE)
        shutil.rmtree(self.area.path)

    def plan(self):
        return o.review(self.area, [self.row], self.receipts, [approval_key(self.row)], self.gates, self.policy)

    def pin_current(self):
        parents = {r['parent'] for r in self.receipts}
        self.policy = o.TrustPolicy(frozenset(map(digest, self.receipts)),
                                   frozenset(digest(r) for r in self.receipts if digest(r) not in parents))

    def state(self):
        return o.inventory(self.area, self.receipts, self.policy)['old.bin']['status']

    def test_verified_and_read_only_handoff(self):
        self.assertEqual(self.state(), 'verified')
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        self.assertTrue(self.auth.revalidate(self.area, plan, token, self.policy)['synthetic_checks_passed'])
        self.assertEqual((self.area.target/'old.bin').read_bytes(), b'old')
        self.assertEqual(list(self.area.sessions.iterdir()), [])

    def test_unverified_not_self_declared(self):
        self.policy = o.TrustPolicy(frozenset())
        self.assertEqual(self.state(), 'unverified')
        with self.assertRaises(ValueError): self.plan()

    def test_tamper_invalidates_pin(self):
        self.receipt['installation'] = 'tampered'
        with self.assertRaises(ValueError): self.state()

    def test_claimed_verified_field_rejected(self):
        self.receipt['verified'] = True
        with self.assertRaises(ValueError): self.state()

    def test_target_binding(self):
        self.receipt['target_id'] = [0, 0]
        with self.assertRaises(ValueError): self.state()

    def test_missing_parent(self):
        self.receipt['parent'] = '0'*64
        with self.assertRaises(ValueError): self.state()

    def test_valid_lineage(self):
        child = dict(self.receipt, installation='install-2', parent=digest(self.receipt))
        self.receipts.append(child)
        self.pin_current()
        self.assertEqual(self.state(), 'verified')
        self.assertEqual(self.plan().as_dict()['ownership']['old.bin']['claims'][0]['installation'], 'install-2')

    def test_unpinned_ancestor(self):
        self.test_valid_lineage()
        self.policy = o.TrustPolicy(frozenset([digest(self.receipts[-1])]), frozenset([digest(self.receipts[-1])]))
        self.assertEqual(self.state(), 'unverified')

    def test_lineage_owner_mismatch(self):
        self.receipts.append(dict(self.receipt, installation='install-2', owner='other', parent=digest(self.receipt)))
        with self.assertRaises(ValueError): self.state()

    def test_forked_lineage(self):
        self.test_valid_lineage()
        self.receipts.append(dict(self.receipt, installation='install-3', parent=digest(self.receipt)))
        self.pin_current()
        self.assertEqual(self.state(), 'conflicting')
        with self.assertRaises(ValueError): self.plan()

    def share(self, content=b'old'):
        second = copy.deepcopy(self.receipt)
        second.update(installation='other-install', owner='other')
        second['files'][0]['expected'] = spec(content)
        self.receipts.append(second)
        self.pin_current()

    def test_shared_preserve_only(self):
        self.share()
        self.assertEqual(self.state(), 'shared')
        with self.assertRaises(ValueError): self.plan()
        self.row.update(action='preserve', source=None, after=None)
        self.plan()

    def test_shared_delete_blocked(self):
        self.share(); self.row.update(action='delete', source=None, after=None)
        with self.assertRaises(ValueError): self.plan()

    def test_conflicting_hashes(self):
        self.share(b'other')
        self.assertEqual(self.state(), 'conflicting')

    def test_duplicate_installation(self):
        self.receipts.append(copy.deepcopy(self.receipt))
        with self.assertRaises(ValueError): self.state()

    def test_unsafe_and_case_collision(self):
        self.receipt['files'].append({'path':'OLD.BIN', 'expected':spec(b'old')})
        with self.assertRaises(ValueError): self.state()
        self.receipt['files'] = [{'path':'../outside', 'expected':spec(b'old')}]
        with self.assertRaises(ValueError): self.state()

    def test_modified_owned_file(self):
        (self.area.target/'old.bin').write_bytes(b'user change')
        self.row['before'] = spec(b'user change')
        with self.assertRaises(ValueError): self.plan()

    def test_expired_consent(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256, ttl=1)
        self.now += 1
        with self.assertRaises(ValueError): self.auth.revalidate(self.area, plan, token, self.policy)

    def test_wrong_explicit_digest(self):
        with self.assertRaises(ValueError): self.auth.issue(self.plan(), '0'*64)

    def test_changed_plan(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        self.row.update(action='delete', source=None, after=None)
        with self.assertRaises(ValueError): self.auth.validate(token, self.plan())

    def test_forged_or_foreign_consent(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        with self.assertRaises(ValueError): o.ConsentAuthority(clock=lambda:self.now).validate(token, plan)
        token['payload']['expires'] += 100
        with self.assertRaises(ValueError): self.auth.validate(token, plan)

    def test_destination_revalidation(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        (self.area.target/'old.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.auth.revalidate(self.area, plan, token, self.policy)

    def test_source_revalidation(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        (self.area.path/'payload'/'new.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.auth.revalidate(self.area, plan, token, self.policy)

    def test_revoked_trust(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        with self.assertRaises(ValueError): self.auth.revalidate(self.area, plan, token, o.TrustPolicy(frozenset()))

    def test_backwards_clock(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        self.now -= 1
        with self.assertRaises(ValueError): self.auth.validate(token, plan)

    def test_create_owner_collision(self):
        (self.area.target/'old.bin').unlink()
        self.row.update(action='create', before=None)
        with self.assertRaises(ValueError): self.plan()

    def test_replaced_root(self):
        plan = self.plan(); token = self.auth.issue(plan, plan.sha256)
        self.area.target.rename(self.area.path/'old-target'); self.area.target.mkdir()
        with self.assertRaises(ValueError): self.auth.revalidate(self.area, plan, token, self.policy)

    def test_omitted_latest_receipt_cannot_roll_back(self):
        self.test_valid_lineage()
        self.receipts.pop()
        with self.assertRaises(ValueError): self.state()
