import copy
import json
import shutil
import unittest
from hf_payload.registry import Registry
from hf_payload.recovery import SyntheticArea, BASE, digest, canonical, SimulatedCrash
from hf_payload.planner import approval_key
from test_planner import spec


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.area = SyntheticArea.create()
        (self.area.path/'payload').mkdir()
        (self.area.path/'payload'/'new.bin').write_bytes(b'new')
        (self.area.target/'old.bin').write_bytes(b'old')
        self.now = 1000
        self.key, self.anchor = b'r'*32, b'a'*32
        self.reg = self.instance()
        self.initial = self.reg.create()
        self.receipt = dict(schema=1, installation='install-1', owner='package', area=self.area.path.name,
                            target_id=self.area.marker['target_id'], parent=None,
                            files=[{'path':'old.bin','expected':spec(b'old')}])
        self.row = dict(destination='old.bin', source='new.bin', action='replace', owner='package', before=spec(b'old'), after=spec(b'new'))
        self.gates = dict(profile='synthetic', licensing=True, provenance=True, compatibility=True, mapping=True)
        self.register([self.receipt])

    def instance(self):
        return Registry(self.area, self.key, self.anchor, clock=lambda:self.now)

    def tearDown(self):
        self.assertEqual(self.area.path.parent, BASE)
        shutil.rmtree(self.area.path)

    def request(self, receipts):
        parents = {r['parent'] for r in receipts}
        return self.reg.anchor_request(receipts, {digest(r) for r in receipts}, {digest(r) for r in receipts if digest(r) not in parents})

    def register(self, receipts, fault=lambda _:None):
        req = self.request(receipts)
        return self.reg.update_trust(req, self.reg.approve_anchor(req, digest(req)), fault)

    def plan(self):
        return self.reg.plan([self.row], [approval_key(self.row)], self.gates)

    def crash(self, point):
        def fault(at):
            if at == point: raise SimulatedCrash(at)
        return fault

    def test_restart_receipts_and_token(self):
        plan = self.plan(); token = self.reg.issue(plan, plan.sha256)
        reg = self.instance(); reg.open(self.reg.checkpoint)
        self.assertTrue(reg.consume(plan, token)['consumed'])
        self.assertEqual((self.area.target/'old.bin').read_bytes(), b'old')
        self.assertEqual(list(self.area.sessions.iterdir()), [])

    def test_persistent_replay_refused(self):
        plan = self.plan(); token = self.reg.issue(plan, plan.sha256)
        self.reg.consume(plan, token)
        reg = self.instance(); reg.open(self.reg.checkpoint)
        with self.assertRaises(ValueError): reg.consume(plan, token)

    def test_expiry(self):
        plan = self.plan(); token = self.reg.issue(plan, plan.sha256, 1); self.now += 1
        with self.assertRaises(ValueError): self.reg.consume(plan, token)

    def test_corrupt_bytes(self):
        self.reg.path.write_bytes(b'partial')
        with self.assertRaises(ValueError): self.instance().open(self.reg.checkpoint)

    def test_rehash_is_not_authentication(self):
        data=json.loads(self.reg.path.read_text()); data['state']['trust_version'] += 1
        data['sha256']=digest(data['state']); self.reg.path.write_bytes(canonical(data))
        with self.assertRaises(ValueError): self.instance().open(self.reg.checkpoint)

    def test_wrong_external_key(self):
        reg=Registry(self.area,b'x'*32,self.anchor,clock=lambda:self.now)
        with self.assertRaises(ValueError): reg.open(self.reg.checkpoint)

    def test_anchor_authorization_required(self):
        req=self.request([self.receipt])
        with self.assertRaises(ValueError): self.reg.update_trust(req,'0'*64)

    def test_stale_anchor_change(self):
        req=self.request([self.receipt]); sig=self.reg.approve_anchor(req,digest(req))
        self.reg.update_trust(req,sig)
        with self.assertRaises(ValueError): self.reg.update_trust(req,sig)

    def test_no_silent_trust_downgrade(self):
        req=self.request([self.receipt]); req['trust_version']=0
        with self.assertRaises(ValueError): self.reg.update_trust(req,self.reg.approve_anchor(req,digest(req)))

    def test_no_history_removal(self):
        with self.assertRaises(ValueError): self.register([])

    def test_duplicate_receipts(self):
        with self.assertRaises(ValueError): self.register([self.receipt,self.receipt])

    def test_untrusted_receipt(self):
        req=self.request([self.receipt]); req['pins']=[]; req['heads']=[]
        with self.assertRaises(ValueError): self.reg.update_trust(req,self.reg.approve_anchor(req,digest(req)))

    def test_conflicting_ownership(self):
        other=copy.deepcopy(self.receipt); other.update(installation='other-install',owner='other')
        other['files'][0]['expected']=spec(b'wrong')
        with self.assertRaises(ValueError): self.register([self.receipt,other])

    def test_shared_registry_preserves_no_delete(self):
        other=dict(self.receipt,installation='other-install',owner='other')
        self.register([self.receipt,other])
        with self.assertRaises(ValueError): self.plan()
        self.row.update(action='preserve',source=None,after=None)
        self.plan()

    def test_lineage_extension_and_old_heads_refused(self):
        child=dict(self.receipt,installation='install-2',parent=digest(self.receipt))
        self.register([self.receipt,child]); self.plan()
        req=self.request([self.receipt,child]); req['heads']=[digest(self.receipt)]
        with self.assertRaises(ValueError): self.reg.update_trust(req,self.reg.approve_anchor(req,digest(req)))

    def test_pending_commit_recovered(self):
        checkpoint=dict(self.reg.checkpoint)
        with self.assertRaises(SimulatedCrash): self.register([self.receipt],self.crash('after_pending'))
        reg=self.instance(); next_cp=reg.open(checkpoint)
        self.assertEqual(next_cp['revision'],checkpoint['revision']+1)
        self.assertFalse(reg.pending.exists())

    def test_consumption_pending_is_burned_after_restart(self):
        plan=self.plan(); token=self.reg.issue(plan,plan.sha256); checkpoint=dict(self.reg.checkpoint)
        with self.assertRaises(SimulatedCrash): self.reg.consume(plan,token,self.crash('after_pending'))
        reg=self.instance(); reg.open(checkpoint)
        with self.assertRaises(ValueError): reg.consume(plan,token)

    def test_after_replace_uncertain_commit(self):
        plan=self.plan(); token=self.reg.issue(plan,plan.sha256); checkpoint=dict(self.reg.checkpoint)
        with self.assertRaises(SimulatedCrash): self.reg.consume(plan,token,self.crash('after_replace'))
        reg=self.instance(); reg.open(checkpoint)
        with self.assertRaises(ValueError): reg.consume(plan,token)

    def test_corrupt_pending_refuses_without_overwrite(self):
        before=self.reg.path.read_bytes(); self.reg.pending.write_bytes(b'torn')
        with self.assertRaises(ValueError): self.instance().open(self.reg.checkpoint)
        self.assertEqual(self.reg.path.read_bytes(),before)

    def test_external_checkpoint_detects_rollback(self):
        old=self.reg.path.read_bytes()
        self.register([self.receipt]); latest=dict(self.reg.checkpoint)
        self.reg.path.write_bytes(old)
        with self.assertRaises(ValueError): self.instance().open(latest)

    def test_stale_handle(self):
        reg=self.instance(); reg.open(self.reg.checkpoint)
        self.register([self.receipt])
        with self.assertRaises(ValueError): reg.plan([self.row],[approval_key(self.row)],self.gates)

    def test_trust_change_invalidates_consent(self):
        plan=self.plan(); token=self.reg.issue(plan,plan.sha256)
        self.register([self.receipt])
        with self.assertRaises(ValueError): self.reg.consume(plan,token)

    def test_destination_revalidation(self):
        plan=self.plan(); token=self.reg.issue(plan,plan.sha256)
        (self.area.target/'old.bin').write_bytes(b'user')
        with self.assertRaises(ValueError): self.reg.consume(plan,token)

    def test_changed_plan_and_token_tampering(self):
        plan=self.plan(); token=self.reg.issue(plan,plan.sha256)
        token['body']['expires']+=1
        with self.assertRaises(ValueError): self.reg.consume(plan,token)
        with self.assertRaises(ValueError): self.reg.issue(plan,'0'*64)

    def test_create_no_overwrite(self):
        with self.assertRaises(ValueError): self.reg.create()

    def test_clock_watermark(self):
        self.now-=1
        with self.assertRaises(ValueError): self.plan()
