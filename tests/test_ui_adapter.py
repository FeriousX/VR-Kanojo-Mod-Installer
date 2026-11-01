import copy
import shutil
import unittest
from hf_payload import ui_adapter as adapter
from hf_payload.recovery import BASE


class UIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.area=adapter.new_fixture()
        self.request=dict(schema_version=1,action='validate-selections',components=['core-framework','configuration-tools'],
                          desktop_mode='vrkanojo-desktop',demo_library='demo-a')
        self.gates=dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True)

    def tearDown(self):
        self.assertEqual(self.area.path.parent,BASE); shutil.rmtree(self.area.path)

    def validate(self): return adapter.validate_selection(self.request,self.area,self.gates)

    def test_valid_contract_read_only(self):
        r=self.validate(); self.assertEqual(r['status'],'valid'); self.assertEqual(len(r['operations']),3)
        self.assertEqual(len(r['plan_digest']),64); self.assertFalse(r['execution_authorized'])
        self.assertFalse(r['installation_allowed']); self.assertTrue(r['requires_separate_execution_consent'])
        self.assertEqual(list((self.area.target/'proposal').iterdir()),[])
        self.assertEqual(list(self.area.sessions.iterdir()),[])

    def test_both_single_desktop_choices(self):
        for option in adapter.DESKTOP:
            self.request['desktop_mode']=option
            self.assertEqual(self.validate()['status'],'valid')

    def test_noop(self):
        self.request.update(components=[],desktop_mode='neither')
        r=self.validate(); self.assertEqual(r['status'],'valid'); self.assertIsNone(r['plan_digest'])

    def test_no_paths_or_extra_fields(self):
        self.request['target']='C:/Games'
        self.assertEqual(self.validate()['status'],'blocked')

    def test_reject_wrong_versions_actions_types(self):
        for key,value in [('schema_version',2),('schema_version',True),('action','execute'),('components','all'),('demo_library','C:/Games')]:
            original=copy.deepcopy(self.request); self.request[key]=value
            self.assertEqual(self.validate()['status'],'blocked'); self.request=original

    def test_missing_and_unknown_components(self):
        self.request['components']=['unknown']; self.assertEqual(self.validate()['status'],'blocked')
        del self.request['components']; self.assertEqual(self.validate()['status'],'blocked')

    def test_duplicate_component(self):
        self.request['components']=['core-framework']*2; self.assertEqual(self.validate()['status'],'blocked')

    def test_desktop_mutual_exclusion(self):
        self.request['desktop_mode']=['vrkanojo-desktop','play-without-vr']
        self.assertEqual(self.validate()['status'],'blocked')

    def test_dependencies(self):
        self.request['components']=['configuration-tools']; r=self.validate()
        self.assertEqual(r['status'],'blocked'); self.assertTrue(r['blocked_operations'])

    def test_existing_conflicting_desktop_preserved(self):
        p=self.area.target/'proposal/play-without-vr.txt'; p.write_bytes(b'user fixture')
        self.assertEqual(self.validate()['status'],'blocked'); self.assertEqual(p.read_bytes(),b'user fixture')

    def test_both_existing_plugins(self):
        for option in adapter.DESKTOP[:2]: (self.area.target/'proposal'/(option+'.txt')).write_bytes(b'user')
        self.request['desktop_mode']='neither'; self.assertEqual(self.validate()['status'],'blocked')

    def test_existing_unowned_destination_not_overwritten(self):
        p=self.area.target/'proposal/core-framework.txt'; p.write_bytes(b'user')
        self.assertEqual(self.validate()['status'],'blocked'); self.assertEqual(p.read_bytes(),b'user')

    def test_missing_or_changed_source(self):
        p=self.area.path/'payload/core-framework.txt'; p.write_bytes(b'changed')
        self.assertEqual(self.validate()['status'],'blocked'); p.unlink()
        self.assertEqual(self.validate()['status'],'blocked')

    def test_rights_gates_apply_to_noop_too(self):
        self.request.update(components=[],desktop_mode='neither')
        self.gates['licensing']=False; self.assertEqual(self.validate()['status'],'blocked')

    def test_request_digest_changes_with_choices(self):
        first=self.validate(); self.request['demo_library']='demo-b'
        self.assertNotEqual(first['request_digest'],self.validate()['request_digest'])
