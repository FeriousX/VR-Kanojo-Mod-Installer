import copy
import hashlib
import os
import shutil
import unittest
from unittest import mock
from hf_payload import planner as p
from hf_payload.recovery import SyntheticArea, BASE, snapshot


def spec(data):
    return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.area = SyntheticArea.create()
        (self.area.path / 'payload').mkdir()
        (self.area.path / 'payload' / 'new.bin').write_bytes(b'new')
        (self.area.target / 'old.bin').write_bytes(b'old')
        self.gates = dict(profile='synthetic', compatibility=True, licensing=True, provenance=True, mapping=True)
        self.row = dict(destination='old.bin', source='new.bin', action='replace', owner='test-package',
                        before=spec(b'old'), after=spec(b'new'))
        self.receipt = dict(destination='old.bin', owner='test-package', expected=spec(b'old'), receipt='receipt-1')

    def tearDown(self):
        self.assertEqual(self.area.path.parent, BASE)
        shutil.rmtree(self.area.path)

    def plan(self, rows=None, receipts=None, approvals=None):
        rows = [self.row] if rows is None else rows
        return p.build_plan(self.area, rows, [self.receipt] if receipts is None else receipts,
                            [p.approval_key(r) for r in rows] if approvals is None else approvals, self.gates)

    def test_owned_replace_read_only_and_adapter(self):
        before = snapshot(self.area.target / 'old.bin')
        plan = self.plan()
        self.assertEqual(before, snapshot(self.area.target / 'old.bin'))
        self.assertEqual(list(self.area.sessions.iterdir()), [])
        self.assertFalse(plan.as_dict()['installation_allowed'])
        self.assertEqual(plan.recovery_operations(), [{'path': 'old.bin', 'action': 'replace', 'post': spec(b'new')}])
        self.assertEqual(plan.sha256, self.plan().sha256)

    def test_create(self):
        self.row.update(destination='added.bin', before=None, action='create')
        self.assertEqual(self.plan(receipts=[]).as_dict()['operations'][0]['owner'], 'test-package')

    def test_delete_exact_owned_file(self):
        self.row.update(action='delete', source=None, after=None)
        self.assertEqual(self.plan().recovery_operations()[0]['action'], 'delete')

    def test_preserve_unknown_user_file(self):
        self.row.update(action='preserve', source=None, after=None)
        self.assertEqual(self.plan(receipts=[], approvals=[]).recovery_operations()[0]['action'], 'protect')

    def test_unknown_owner_blocked(self):
        with self.assertRaises(ValueError): self.plan(receipts=[])

    def test_wrong_owner_blocked(self):
        self.receipt['owner'] = 'other'
        with self.assertRaises(ValueError): self.plan()

    def test_user_modified_even_if_approved(self):
        (self.area.target / 'old.bin').write_bytes(b'edited')
        self.row['before'] = spec(b'edited')
        with self.assertRaises(ValueError): self.plan()

    def test_missing_approval(self):
        with self.assertRaises(ValueError): self.plan(approvals=[])

    def test_changed_request_invalidates_approval(self):
        approval = p.approval_key(self.row)
        self.row['owner'] = 'new-owner'
        with self.assertRaises(ValueError): self.plan(approvals=[approval])

    def test_review_gates(self):
        for key in ('compatibility', 'licensing', 'provenance', 'mapping'):
            with self.subTest(key=key):
                self.gates[key] = False
                with self.assertRaises(ValueError): self.plan()
                self.gates[key] = True
        self.gates['profile'] = 'inspection'
        with self.assertRaises(ValueError): self.plan()

    def test_paths(self):
        for name in ('../bad', 'C:/bad', '/bad', 'x:ads', 'CON', 'bad.', 'a//b', '\\\\server\\file'):
            for field in ('source', 'destination'):
                with self.subTest(name=name, field=field):
                    row = dict(self.row, **{field: name})
                    with self.assertRaises(ValueError): self.plan([row])

    def test_case_and_ancestor_collisions(self):
        for dest in ('OLD.BIN', 'old.bin/child'):
            with self.subTest(dest=dest):
                with self.assertRaises(ValueError): self.plan([self.row, dict(self.row, destination=dest)])

    def test_bad_source_hash_and_missing_mapping(self):
        for source in ('missing.bin', None):
            self.row['source'] = source
            with self.assertRaises((ValueError, TypeError)): self.plan()
        self.row['source'] = 'new.bin'
        self.row['after'] = spec(b'wrong')
        with self.assertRaises(ValueError): self.plan()

    def test_bad_destination_hash(self):
        self.row['before'] = spec(b'wrong')
        with self.assertRaises(ValueError): self.plan()

    def test_no_directory_delete(self):
        self.row.update(action='delete-directory')
        with self.assertRaises(ValueError): self.plan()
        (self.area.target / 'folder').mkdir()
        self.row.update(action='delete', destination='folder', source=None, after=None)
        with self.assertRaises(ValueError): self.plan()

    def test_duplicate_receipts(self):
        with self.assertRaises(ValueError): self.plan(receipts=[self.receipt, self.receipt])

    def test_strict_schemas_and_owner(self):
        for change in ({'extra': 1}, {'owner': ''}, {'after': {'size': True, 'sha256': '0'*64}}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.plan([dict(self.row, **change)])

    def test_target_replaced_identity(self):
        self.area.target.rename(self.area.path / 'previous-target')
        self.area.target.mkdir()
        with self.assertRaises(ValueError): self.plan()

    def test_hardlinked_source(self):
        os.link(self.area.path / 'payload' / 'new.bin', self.area.path / 'alias')
        with self.assertRaises(ValueError): self.plan()

    def test_symlink_source(self):
        path = self.area.path / 'payload' / 'link.bin'
        try:
            path.symlink_to(self.area.path / 'payload' / 'new.bin')
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable; junction rejection qualified separately')
            raise
        self.row['source'] = 'link.bin'
        with self.assertRaises(ValueError): self.plan()

    def test_missing_parent(self):
        self.row.update(destination='missing/new.bin', before=None, action='create')
        with self.assertRaises(OSError): self.plan()

    def test_access_error(self):
        with mock.patch.object(p, 'snapshot', side_effect=PermissionError('synthetic denial')):
            with self.assertRaises(PermissionError): self.plan()

    def test_change_during_scan(self):
        original = p.snapshot
        count = 0
        def changing(path):
            nonlocal count
            count += 1
            if count == 3: (self.area.target / 'old.bin').write_bytes(b'changed')
            return original(path)
        with mock.patch.object(p, 'snapshot', side_effect=changing):
            with self.assertRaises(ValueError): self.plan()

    def test_no_mutable_plan_alias(self):
        plan = self.plan()
        data = plan.as_dict()
        data['operations'].clear()
        self.assertEqual(len(plan.as_dict()['operations']), 1)

    def test_multi_operation(self):
        second = dict(self.row, destination='second.bin', before=None, action='create')
        self.assertEqual(len(self.plan([self.row, second]).recovery_operations()), 2)

    def test_unexpected_existing_create(self):
        self.row['action'] = 'create'
        with self.assertRaises(ValueError): self.plan()

