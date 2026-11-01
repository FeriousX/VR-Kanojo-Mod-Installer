import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gui_install as gui
from hf_payload.recovery import BASE, SyntheticArea, read_json


class GUIInstallTests(unittest.TestCase):
    def setUp(self): self.jobs=[]
    def tearDown(self):
        for meta in self.jobs:
            if meta.get('bridge_id'):
                area=SyntheticArea(BASE/meta['bridge_id']);shutil.rmtree(area.path)
            folder=gui.EXCHANGE/meta['job']
            if folder.exists():shutil.rmtree(folder)

    def prepare(self,desktop='neither',mask=3):
        job=uuid.uuid4().hex*2
        meta=gui.prepare_job(job,mask,desktop,'demo-a');self.jobs.append(meta)
        return meta
    def frame(self,meta): return read_json(gui.folder_for(meta['job'])/'frame.json')

    def test_actual_execution_all_modes(self):
        for mode in ('neither','vrkanojo-desktop','play-without-vr'):
            meta=self.prepare(mode); before=self.frame(meta)
            self.assertEqual(before['state'],'Prepared');self.assertEqual(before['success'],'0')
            result=gui.run_job(meta['job'],meta['plan_digest']);frame=self.frame(meta)
            self.assertEqual(result['status'],'CommittedSynthetic');self.assertEqual(frame['state'],'Completed')
            self.assertEqual(frame['percent'],'100');self.assertEqual(frame['success'],'1')
            self.assertTrue(result['transaction_id']);self.assertTrue(result['backups_verified'])
            self.assertEqual((BASE/meta['bridge_id']/'target/unrelated.txt').read_bytes(),b'Unowned synthetic user text - preserve.\n')

    def test_frozen_recovery_instruction_uses_packaged_command(self):
        meta=self.prepare()
        with mock.patch.object(sys,'frozen',True,create=True):
            gui.run_job(meta['job'],meta['plan_digest'])
        frame=self.frame(meta)
        self.assertTrue(any('Recovery: HFBackend.exe install recover --id ' in value for value in frame.values()))
        self.assertFalse(any('synthetic_install.py' in value for value in frame.values()))

    def test_consent_digest_required(self):
        meta=self.prepare()
        for consent in ('',None,'0'*64):
            with self.assertRaises(ValueError):gui.run_job(meta['job'],consent)
        self.assertFalse((BASE/meta['bridge_id']/'coordinator-intent.json').exists())

    def test_expired_review_window(self):
        meta=self.prepare()
        with self.assertRaises(ValueError):gui.run_job(meta['job'],meta['plan_digest'],clock=lambda:meta['created']+601)

    def test_duplicate_worker_cannot_overwrite_success(self):
        meta=self.prepare();gui.run_job(meta['job'],meta['plan_digest'])
        before=(gui.folder_for(meta['job'])/'frame.json').read_bytes()
        with self.assertRaises(FileExistsError):gui.run_job(meta['job'],meta['plan_digest'])
        self.assertEqual((gui.folder_for(meta['job'])/'frame.json').read_bytes(),before)

    def test_failed_validation(self):
        meta=self.prepare(mask=2)
        self.assertEqual(self.frame(meta)['state'],'Blocked');self.assertFalse(meta['plan_digest'])

    def test_failure_restores_and_never_says_success(self):
        meta=self.prepare()
        def fault(point,index):
            if point=='after_publish' and index==1:raise OSError('injected failure')
        result=gui.run_job(meta['job'],meta['plan_digest'],extra_fault=fault)
        self.assertEqual(result['status'],'Recovered');self.assertEqual(self.frame(meta)['success'],'0')
        self.assertEqual(self.frame(meta)['state'],'Failed');self.assertEqual(self.frame(meta)['percent'],'')

    def test_malformed_output_state_rejected(self):
        meta=self.prepare();folder=gui.folder_for(meta['job'])
        for state,final,success in [('Completed',False,True),('Applying',True,False),('Unknown',True,False),('Completed',True,False)]:
            with self.assertRaises(ValueError):gui.publish(folder,meta,state,['x'],final,success)
        with self.assertRaises(ValueError):gui.publish(folder,meta,'Failed',['x\nbad'],True)

    def test_worker_lock_blocks_concurrent_execution(self):
        meta=self.prepare()
        with gui.worker_lock(gui.folder_for(meta['job'])):
            with self.assertRaises(OSError):gui.run_job(meta['job'],meta['plan_digest'])

    def test_no_arbitrary_job_path(self):
        for value in ('../escape','C:/Games','a'*63):
            with self.assertRaises(ValueError):gui.folder_for(value)

    def test_async_child_real_progress(self):
        meta=self.prepare()
        code=("import sys,time;sys.path.insert(0,"+repr(str(gui.WORKSPACE/'tools'))+");import gui_install as g;"
              "g.run_job("+repr(meta['job'])+","+repr(meta['plan_digest'])+",extra_fault=lambda p,i:time.sleep(.3) if p=='after_backup' else None)")
        child=subprocess.Popen([sys.executable,'-I','-S','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            deadline=time.monotonic()+20; observed=False
            while child.poll() is None and time.monotonic()<deadline:
                frame=self.frame(meta)
                if frame['state'] in ('Validating','BackingUp','Applying','Verifying'):
                    self.assertEqual(frame['success'],'0');self.assertEqual(frame['percent'],'');observed=True
                time.sleep(.025)
            output,error=child.communicate(timeout=20)
            self.assertEqual(child.returncode,0,error);self.assertTrue(observed)
            self.assertEqual(self.frame(meta)['state'],'Completed',self.frame(meta))
        finally:
            if child.poll() is None: child.wait(timeout=30)

    def test_child_exit_then_explicit_recovery(self):
        meta=self.prepare()
        code=("import sys,os;sys.path.insert(0,"+repr(str(gui.WORKSPACE/'tools'))+");import gui_install as g;"
              "g.run_job("+repr(meta['job'])+","+repr(meta['plan_digest'])+",extra_fault=lambda p,i:os._exit(87) if p=='after_publish' and i==1 else None)")
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,87);self.assertEqual(self.frame(meta)['success'],'0')
        recovered=gui.run_job(meta['job'],None,recover=True)
        self.assertEqual(recovered['status'],'Recovered');self.assertEqual(self.frame(meta)['state'],'Failed')

    def test_response_hash_projection(self):
        meta=self.prepare();folder=gui.folder_for(meta['job'])
        raw=(folder/'frame.json').read_bytes();ini=(folder/'frame.ini').read_text()
        self.assertIn('response_sha256 = '+hashlib.sha256(raw).hexdigest(),ini)
        self.assertEqual(self.frame(meta)['binding'],'3|neither|demo-a')

    def test_transient_reader_lock_publication_retry(self):
        from unittest import mock
        meta=self.prepare();replace=gui.os.replace;calls=[]
        def transient(source,target):
            calls.append(1)
            if len(calls)==1:raise PermissionError('synthetic reader denies delete sharing')
            return replace(source,target)
        with mock.patch.object(gui.os,'replace',side_effect=transient):
            gui.publish(gui.folder_for(meta['job']),meta,'Validating',['Actual validation in progress'])
        self.assertEqual(self.frame(meta)['state'],'Validating')

    def test_real_cli_prepare_run_isolated_python(self):
        job=uuid.uuid4().hex*2
        command=[sys.executable,'-I','-S','-B',str(Path(gui.__file__))]
        prepared=subprocess.run(command+['prepare','--job',job,'--mask','3','--desktop','neither','--library','demo-a'],
                                capture_output=True,text=True,timeout=20)
        self.assertEqual(prepared.returncode,0,prepared.stderr)
        meta=read_json(gui.EXCHANGE/job/'job.json');self.jobs.append(meta)
        executed=subprocess.run(command+['run','--job',job,'--approve-plan',meta['plan_digest']],
                                capture_output=True,text=True,timeout=20)
        self.assertEqual(executed.returncode,0,executed.stderr)
        self.assertEqual(self.frame(meta)['state'],'Completed')
