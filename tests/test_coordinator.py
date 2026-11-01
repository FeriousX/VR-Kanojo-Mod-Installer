import copy
import shutil
import unittest
from hf_payload.coordinator import Coordinator
from hf_payload.registry import Registry
from hf_payload.recovery import SyntheticArea, BASE, digest, SimulatedCrash, snapshot
from hf_payload.planner import approval_key
from test_planner import spec


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.area=SyntheticArea.create(); self.root=self.area.target
        (self.area.path/'payload').mkdir()
        (self.area.path/'payload/new.bin').write_bytes(b'new')
        for path,data in {'old.txt':b'old','obsolete.txt':b'obsolete','custom.txt':b'user','unrelated.txt':b'unrelated'}.items():
            (self.root/path).write_bytes(data)
        self.before={p.name:snapshot(p) for p in self.root.iterdir()}
        self.keys=(b'r'*32,b'a'*32,b't'*32)
        self.reg=Registry(self.area,*self.keys[:2],clock=lambda:1000)
        self.reg.create()
        self.receipt=dict(schema=1,installation='prior-install',owner='package',area=self.area.path.name,
                          target_id=self.area.marker['target_id'],parent=None,
                          files=[{'path':'old.txt','expected':spec(b'old')},{'path':'obsolete.txt','expected':spec(b'obsolete')}])
        request=self.reg.anchor_request([self.receipt],{digest(self.receipt)},{digest(self.receipt)})
        self.reg.update_trust(request,self.reg.approve_anchor(request,digest(request)))
        self.initial=self.reg._current()
        self.co=Coordinator(self.area,self.reg,self.keys[2])
        self.gates=dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True)
        self.rows=[self.row('old.txt','replace',b'old'),self.row('new.txt','create',None),
                   self.row('obsolete.txt','delete',b'obsolete'),self.row('custom.txt','preserve',b'user')]

    def row(self,path,action,before):
        return dict(destination=path,source='new.bin' if action in ('create','replace') else None,
                    action=action,owner='package',before=spec(before) if before is not None else None,
                    after=spec(b'new') if action in ('create','replace') else None)

    def tearDown(self):
        self.assertEqual(self.area.path.parent,BASE); shutil.rmtree(self.area.path)

    def authorize(self):
        plan=self.reg.plan(self.rows,[approval_key(r) for r in self.rows],self.gates)
        return plan,self.reg.issue(plan,plan.sha256),self.co.authorize(plan,plan.sha256)

    def original(self):
        for name,data in {'old.txt':b'old','obsolete.txt':b'obsolete','custom.txt':b'user','unrelated.txt':b'unrelated'}.items():
            self.assertEqual((self.root/name).read_bytes(),data)
        self.assertFalse((self.root/'new.txt').exists())

    def crash(self,point,index=None):
        def fault(at,i):
            if at==point and (index is None or i==index): raise SimulatedCrash(at)
        return fault

    def restart(self):
        reg=Registry(self.area,*self.keys[:2],clock=lambda:1000)
        reg.open(self.reg.checkpoint)
        return Coordinator(self.area,reg,self.keys[2])

    def test_success_all_actions_and_receipts(self):
        args=self.authorize(); result=self.co.execute(*args)
        self.assertEqual(result['status'],'CommittedSynthetic')
        self.assertEqual((self.root/'old.txt').read_bytes(),b'new')
        self.assertEqual((self.root/'new.txt').read_bytes(),b'new')
        self.assertFalse((self.root/'obsolete.txt').exists())
        self.assertEqual(snapshot(self.root/'custom.txt'),self.before['custom.txt'])
        self.assertEqual(snapshot(self.root/'unrelated.txt'),self.before['unrelated.txt'])
        receipt=self.reg._current()['receipts'][-1]
        self.assertEqual(receipt['parent'],digest(self.receipt))
        self.assertEqual({f['path'] for f in receipt['files']},{'old.txt','new.txt'})
        self.assertFalse(result['installation_allowed'])

    def test_partial_failure_recovers_before_ownership(self):
        def fail(point,i):
            if point=='after_publish' and i==1: raise OSError('injected operation failure')
        result=self.co.execute(*self.authorize(),fault=fail)
        self.assertEqual(result['status'],'Recovered'); self.original()
        self.assertEqual(self.reg._current()['receipts'],self.initial['receipts'])

    def test_interrupted_publication_restart_recovery(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('after_publish',1))
        restarted=self.restart()
        self.assertEqual(restarted.recover()['status'],'Recovered'); self.original()
        self.assertEqual(restarted.recover()['status'],'Recovered')

    def test_interrupted_completed_files_recover(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('after_files'))
        self.assertEqual(self.restart().recover()['status'],'Recovered'); self.original()

    def test_interrupted_registry_pending_rolls_forward(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('registry_after_pending'))
        restarted=self.restart()
        self.assertEqual(restarted.recover()['status'],'CommittedSynthetic')
        self.assertEqual((self.root/'old.txt').read_bytes(),b'new')

    def test_interrupted_registry_after_replace(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('registry_after_replace'))
        self.assertEqual(self.restart().recover()['status'],'CommittedSynthetic')

    def test_interrupted_after_registry_no_rollback(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('after_registry'))
        self.assertEqual(self.restart().recover()['status'],'CommittedSynthetic')

    def test_interrupted_after_consent_no_target_writes(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('after_consent'))
        self.assertEqual(self.restart().recover()['status'],'AbortedNoTargetWrites'); self.original()

    def test_duplicate_execution_refused(self):
        args=self.authorize(); self.co.execute(*args)
        with self.assertRaises(ValueError): self.co.execute(*args)

    def test_consumed_consent_cannot_be_replayed(self):
        args=self.authorize(); self.reg.consume(args[0],args[1])
        with self.assertRaises(ValueError): self.co.execute(*args)
        self.original()

    def test_untrusted_context_refused(self):
        plan,token,context=self.authorize(); context['body']['scope']='production'
        with self.assertRaises(ValueError): self.co.execute(plan,token,context)
        self.original(); self.assertFalse(self.co.intent.exists())

    def test_changed_destination_refused_before_intent(self):
        args=self.authorize(); (self.root/'old.txt').write_bytes(b'user modified')
        with self.assertRaises(ValueError): self.co.execute(*args)
        self.assertEqual((self.root/'old.txt').read_bytes(),b'user modified')

    def test_unowned_file_replacement_refused(self):
        self.rows=[self.row('custom.txt','replace',b'user')]
        with self.assertRaises(ValueError): self.authorize()

    def test_changed_source_after_consent(self):
        def change(point,i):
            if point=='after_consent': (self.area.path/'payload/new.bin').write_bytes(b'changed')
        result=self.co.execute(*self.authorize(),fault=change)
        self.assertEqual(result['status'],'AbortedNoTargetWrites'); self.original()

    def test_changed_new_file_not_deleted_by_recovery(self):
        def fail(point,i):
            if point=='after_applied' and i==1:
                (self.root/'new.txt').write_bytes(b'user edit')
                raise OSError('injected failure')
        result=self.co.execute(*self.authorize(),fault=fail)
        self.assertEqual(result['status'],'RecoveryRequired')
        self.assertEqual((self.root/'new.txt').read_bytes(),b'user edit')
        self.assertEqual(self.reg._current()['receipts'],self.initial['receipts'])

    def test_delete_last_owned_files_keeps_lineage(self):
        self.rows=[self.row('old.txt','delete',b'old'),self.row('obsolete.txt','delete',b'obsolete')]
        result=self.co.execute(*self.authorize()); self.assertEqual(result['status'],'CommittedSynthetic')
        self.assertEqual(self.reg._current()['receipts'][-1]['files'],[])

    def test_wrong_synthetic_root_refused(self):
        other=SyntheticArea.create()
        try:
            with self.assertRaises(ValueError): Coordinator(other,self.reg,self.keys[2])
        finally: shutil.rmtree(other.path)

    def test_rights_gate_not_bypassed(self):
        self.gates['licensing']=False
        with self.assertRaises(ValueError): self.authorize()

    def test_unsafe_or_conflicting_operations(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.authorize()
        self.rows=[self.row('../escape','create',None)]
        with self.assertRaises(ValueError): self.authorize()

    def test_signed_intent_corruption_blocks_recovery(self):
        with self.assertRaises(SimulatedCrash): self.co.execute(*self.authorize(),fault=self.crash('after_backup'))
        self.co.intent.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.co.recover()
        self.original()

    def test_expired_consent_no_writes(self):
        args=self.authorize(); self.reg.clock=lambda:2000
        self.assertEqual(self.co.execute(*args)['status'],'AbortedNoTargetWrites')
        self.original()

    def test_forged_consent_no_writes(self):
        plan,token,context=self.authorize(); token['mac']='0'*64
        self.assertEqual(self.co.execute(plan,token,context)['status'],'AbortedNoTargetWrites')
        self.original()

    def test_backup_failure_never_opens_mutation_gate(self):
        def fail(point,index):
            if point=='before_backup_gate': raise OSError('injected backup failure')
        with self.assertRaises(ValueError): self.co.execute(*self.authorize(),fault=fail)
        self.original()
        self.assertEqual(self.reg._current()['receipts'],self.initial['receipts'])

    def test_commit_io_failure_before_publication_recovers(self):
        from unittest import mock
        args=self.authorize()
        with mock.patch.object(self.reg,'update_trust',side_effect=OSError('injected registry failure')):
            self.assertEqual(self.co.execute(*args)['status'],'Recovered')
        self.original()

    def test_post_commit_user_edit_refused_without_rollback(self):
        self.co.execute(*self.authorize()); (self.root/'old.txt').write_bytes(b'new user edit')
        with self.assertRaises(ValueError): self.co.recover()
        self.assertEqual((self.root/'old.txt').read_bytes(),b'new user edit')

    def test_stale_external_checkpoint_is_not_bypassed(self):
        checkpoint=dict(self.reg.checkpoint)
        self.co.execute(*self.authorize())
        reg=Registry(self.area,*self.keys[:2],clock=lambda:1000)
        with self.assertRaises(ValueError): reg.open(checkpoint)

    def test_non_area_target_cannot_be_designated(self):
        from types import SimpleNamespace
        with self.assertRaises(ValueError): Coordinator(SimpleNamespace(path=self.root),self.reg,self.keys[2])
