import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest import mock

from hf_payload import recovery as engine
from hf_payload.recovery import JournalError, SafetyError, SimulatedCrash, SyntheticArea, Transaction, snapshot


def op(path, action, data=None):
    return {"path": path, "action": action, "post": None if data is None else {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}}


def crash(point, index):
    def inject(at, i):
        if (at, i) == (point, index):
            raise SimulatedCrash(at)
    return inject


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.area = SyntheticArea.create()
        self.target = self.area.target
        (self.target / "original.txt").write_bytes(b"original bytes")
        (self.target / "mod.txt").write_bytes(b"custom mod bytes")
        (self.target / "protected").mkdir()
        (self.target / "protected" / "save.txt").write_bytes(b"synthetic user save")
        self.original = snapshot(self.target / "original.txt")

    def tearDown(self):
        # Only an engine-created synthetic area owned by this test is deleted.
        self.assertEqual(self.area.path.parent, engine.BASE)
        for p in self.area.path.rglob("*"):
            if p.is_file() and not p.is_symlink():
                os.chmod(p, 0o666)
        shutil.rmtree(self.area.path)

    def prepare_replace(self):
        return self.area.prepare([op("original.txt", "replace", b"new bytes")])

    def apply_replace(self):
        tx = self.prepare_replace()
        tx.simulate_apply({"original.txt": b"new bytes"})
        return tx

    def test_backup_sha_bytes_and_metadata(self):
        tx = self.prepare_replace(); manifest = tx.verify()
        before = manifest["before"][0]
        self.assertEqual(before, self.original)
        self.assertEqual((tx.folder / "blobs" / before["sha256"]).read_bytes(), b"original bytes")
        self.assertEqual(tx.inspect()["state"], "BackedUp")
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_multiple_operations_and_snapshot_only_protection(self):
        tx = self.area.prepare([op("original.txt", "replace", b"new"), op("new.txt", "create", b"created"),
                                op("mod.txt", "delete"), op("protected/save.txt", "protect")])
        tx.simulate_apply({"original.txt": b"new", "new.txt": b"created"})
        self.assertEqual(tx.inspect()["state"], "Completed")
        self.assertEqual(tx.inspect()["pending"], [])
        (self.target / "protected" / "save.txt").write_bytes(b"new user save")
        result = tx.recover()
        self.assertEqual(result["state"], "Recovered")
        self.assertEqual((self.target / "original.txt").read_bytes(), b"original bytes")
        self.assertEqual((self.target / "mod.txt").read_bytes(), b"custom mod bytes")
        self.assertFalse((self.target / "new.txt").exists())
        self.assertEqual((self.target / "protected/save.txt").read_bytes(), b"new user save")

    def test_absent_snapshot_recorded(self):
        tx = self.area.prepare([op("missing.txt", "create", b"hello"), op("absent-save.txt", "protect")])
        self.assertEqual(tx.verify()["before"], [{"exists": False}, {"exists": False}])

    def test_restore_original_modification_time_and_mode(self):
        tx = self.apply_replace(); tx.recover()
        self.assertTrue(engine.content_matches(snapshot(self.target / "original.txt"), self.original))

    def test_repeat_recovery_is_noop(self):
        tx = self.apply_replace(); tx.recover()
        old = (tx.folder / "journal.jsonl").read_bytes()
        self.assertTrue(tx.recover()["idempotent"])
        self.assertEqual((tx.folder / "journal.jsonl").read_bytes(), old)

    def test_recover_backedup_but_unapplied(self):
        tx = self.prepare_replace()
        self.assertEqual(tx.recover()["state"], "Recovered")
        self.assertEqual((self.target / "original.txt").read_bytes(), b"original bytes")

    def test_crash_after_intent_before_publication(self):
        tx = self.prepare_replace()
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"original.txt": b"new bytes"}, crash("after_intent", 0))
        self.assertTrue(tx.inspect()["interrupted"])
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_crash_after_replace_before_receipt(self):
        tx = self.prepare_replace()
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"original.txt": b"new bytes"}, crash("after_publish", 0))
        self.assertEqual(tx.inspect()["applied"], [])
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_crash_after_new_file_publish_uses_stage_file_identity(self):
        tx = self.area.prepare([op("new.txt", "create", b"created")])
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"new.txt": b"created"}, crash("after_publish", 0))
        self.assertEqual(tx.recover()["state"], "Recovered")
        self.assertFalse((self.target / "new.txt").exists())

    def test_crash_after_delete_before_receipt(self):
        tx = self.area.prepare([op("mod.txt", "delete")])
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({}, crash("after_publish", 0))
        self.assertEqual(tx.recover()["state"], "Recovered")
        self.assertEqual((self.target / "mod.txt").read_bytes(), b"custom mod bytes")

    def test_crash_after_receipt_before_completed(self):
        tx = self.prepare_replace()
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"original.txt": b"new bytes"}, crash("after_applied", 0))
        self.assertEqual(tx.inspect()["applied"], [0])
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_partial_recovery_continues_independent_safe_files(self):
        tx = self.area.prepare([op("original.txt", "replace", b"new"), op("new.txt", "create", b"created")])
        tx.simulate_apply({"original.txt": b"new", "new.txt": b"created"})
        (self.target / "original.txt").write_bytes(b"user edit")
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertFalse((self.target / "new.txt").exists())
        self.assertEqual((self.target / "original.txt").read_bytes(), b"user edit")
        self.assertTrue(tx.inspect()["errors"])

    def test_changed_new_file_is_never_deleted(self):
        tx = self.area.prepare([op("new.txt", "create", b"created")]); tx.simulate_apply({"new.txt": b"created"})
        (self.target / "new.txt").write_bytes(b"user creation")
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertEqual((self.target / "new.txt").read_bytes(), b"user creation")

    def test_same_bytes_but_user_metadata_change_is_conflict(self):
        tx = self.apply_replace(); p = self.target / "original.txt"
        os.utime(p, ns=(p.stat().st_atime_ns, p.stat().st_mtime_ns + 2000000000))
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertEqual(p.read_bytes(), b"new bytes")

    def test_lookalike_unowned_new_file_after_intent_not_deleted(self):
        tx = self.area.prepare([op("new.txt", "create", b"created")])
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"new.txt": b"created"}, crash("after_intent", 0))
        (self.target / "new.txt").write_bytes(b"created")
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertTrue((self.target / "new.txt").exists())

    def test_metadata_change_after_crash_without_receipt_is_preserved(self):
        tx = self.area.prepare([op("new.txt", "create", b"created")])
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"new.txt": b"created"}, crash("after_publish", 0))
        path = self.target / "new.txt"
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 2000000000))
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertTrue(path.exists())

    def test_oversized_total_plan_refused_without_writing(self):
        rows = [{"path": f"large-{i}", "action": "create", "post": {"size": engine.MAX_FILE, "sha256": "0" * 64}} for i in range(5)]
        with self.assertRaises(SafetyError):
            self.area.prepare(rows)
        self.assertEqual(list(self.area.sessions.iterdir()), [])

    def test_change_after_backup_blocks_all_apply(self):
        tx = self.prepare_replace(); (self.target / "original.txt").write_bytes(b"user edit")
        with self.assertRaises(SafetyError):
            tx.simulate_apply({"original.txt": b"new bytes"})
        self.assertEqual((self.target / "original.txt").read_bytes(), b"user edit")

    def test_change_after_intent_is_not_overwritten(self):
        tx = self.prepare_replace()
        def change(point, i):
            if point == "after_intent":
                (self.target / "original.txt").write_bytes(b"user edit")
        with self.assertRaises(SafetyError):
            tx.simulate_apply({"original.txt": b"new bytes"}, change)
        self.assertEqual((self.target / "original.txt").read_bytes(), b"user edit")

    def test_wrong_postimage_does_not_modify_target(self):
        tx = self.prepare_replace()
        with self.assertRaises(SafetyError):
            tx.simulate_apply({"original.txt": b"wrong"})
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_final_apply_verification_detects_postreceipt_edit(self):
        tx = self.prepare_replace()
        def edit(point, i):
            if point == "after_applied":
                (self.target / "original.txt").write_bytes(b"user edit after receipt")
        with self.assertRaises(SafetyError):
            tx.simulate_apply({"original.txt": b"new bytes"}, edit)
        self.assertEqual(tx.inspect()["state"], "RecoveryRequired")
        self.assertEqual((self.target / "original.txt").read_bytes(), b"user edit after receipt")

    def test_final_recovery_verification_detects_prior_restored_file_edit(self):
        tx = self.area.prepare([op("original.txt", "replace", b"new"), op("mod.txt", "replace", b"replacement")])
        tx.simulate_apply({"original.txt": b"new", "mod.txt": b"replacement"})
        def edit(point, i):
            if point == "after_restore_publish" and i == 0:
                (self.target / "mod.txt").write_bytes(b"user edit after earlier restore")
        self.assertEqual(tx.recover(fault=edit)["state"], "RecoveryRequired")
        self.assertEqual((self.target / "mod.txt").read_bytes(), b"user edit after earlier restore")

    def test_failed_backup_never_opens_mutation_gate(self):
        def fail(point, i):
            if point == "before_backup":
                raise PermissionError("synthetic denial")
        with self.assertRaises(PermissionError):
            self.area.prepare([op("original.txt", "delete")], fail)
        folder = next(self.area.sessions.iterdir()); tx = Transaction(self.area, folder.name)
        self.assertFalse(tx.inspect()["backup_gate_recorded"])
        with self.assertRaises((SafetyError, OSError)):
            tx.simulate_apply({})
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_corrupted_backup_before_gate_rejected(self):
        def corrupt(point, i):
            if point == "after_backup_copy":
                folder = next(self.area.sessions.iterdir()); next((folder / "blobs").iterdir()).write_bytes(b"bad")
        with self.assertRaises(SafetyError):
            self.area.prepare([op("original.txt", "delete")], corrupt)
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_enospc_during_copy_keeps_incomplete_backup_and_original(self):
        def full(src, dst, length):
            dst.write(b"partial")
            raise OSError(28, "synthetic disk full")
        with mock.patch("hf_payload.recovery.shutil.copyfileobj", side_effect=full):
            with self.assertRaises(OSError):
                self.prepare_replace()
        tx = Transaction(self.area, next(self.area.sessions.iterdir()).name)
        self.assertFalse(tx.inspect()["backup_gate_recorded"])
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_interrupted_incomplete_backup_cannot_apply(self):
        with self.assertRaises(SimulatedCrash):
            self.area.prepare([op("original.txt", "delete"), op("mod.txt", "delete")], crash("before_backup", 1))
        info = self.area.inspect_sessions()[0]
        self.assertTrue(info["interrupted"])
        self.assertFalse(info["backup_gate_recorded"])
        tx = Transaction(self.area, info["txid"])
        with self.assertRaises((SafetyError, OSError)):
            tx.simulate_apply({})
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_empty_session_after_creation_crash_is_reported(self):
        import uuid
        (self.area.sessions / str(uuid.uuid4())).mkdir()
        info = self.area.inspect_sessions()[0]
        self.assertTrue(info["interrupted"])
        self.assertIsNone(info["state"])

    def test_recreated_user_file_after_delete_is_preserved(self):
        tx = self.area.prepare([op("mod.txt", "delete")]); tx.simulate_apply({})
        (self.target / "mod.txt").write_bytes(b"new user mod")
        self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertEqual((self.target / "mod.txt").read_bytes(), b"new user mod")

    def test_missing_backup_refuses_any_recovery_writes(self):
        tx = self.apply_replace(); blob = tx.folder / "blobs" / self.original["sha256"]; blob.unlink()
        with self.assertRaises((SafetyError, OSError)):
            tx.recover()
        self.assertEqual((self.target / "original.txt").read_bytes(), b"new bytes")
        self.assertEqual(tx.inspect()["state"], "RecoveryRequired")

    def test_corrupt_backup_can_be_replaced_with_verified_bytes_then_retry(self):
        tx = self.apply_replace(); blob = tx.folder / "blobs" / self.original["sha256"]; blob.write_bytes(b"bad")
        with self.assertRaises(SafetyError):
            tx.recover()
        blob.write_bytes(b"original bytes")  # Test operator repairs its own synthetic fixture.
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_retry_after_partial_access_failure(self):
        tx = self.apply_replace()
        def deny(point, i):
            if point == "before_restore":
                raise PermissionError("synthetic locked target")
        self.assertEqual(tx.recover(fault=deny)["state"], "RecoveryRequired")
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_retry_after_restore_publish_crash(self):
        tx = self.apply_replace()
        with self.assertRaises(SimulatedCrash):
            tx.recover(fault=crash("after_restore_publish", 0))
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_corrupt_manifest_stops_recovery(self):
        tx = self.apply_replace(); manifest = tx.folder / "manifest.json"
        data = json.loads(manifest.read_text()); data["plan"][0]["path"] = "../escape"
        manifest.write_text(json.dumps(data))
        with self.assertRaises(SafetyError):
            tx.recover()
        self.assertEqual((self.target / "original.txt").read_bytes(), b"new bytes")

    def test_corrupt_complete_journal_never_auto_repaired(self):
        tx = self.apply_replace(); journal = tx.folder / "journal.jsonl"
        raw = journal.read_bytes(); journal.write_bytes(raw.replace(b'"Completed"', b'"Prepared"'))
        corrupted = journal.read_bytes()
        with self.assertRaises(JournalError):
            tx.recover(repair_torn_tail=True)
        self.assertEqual(journal.read_bytes(), corrupted)
        self.assertEqual((self.target / "original.txt").read_bytes(), b"new bytes")

    def test_illegal_journal_state_rejected_before_append(self):
        tx = self.prepare_replace(); path = tx.folder / "journal.jsonl"; raw = path.read_bytes()
        with self.assertRaises(JournalError):
            tx.journal.state("Completed")
        self.assertEqual(path.read_bytes(), raw)

    def test_unknown_journal_event_rejected_before_append(self):
        tx = self.prepare_replace(); path = tx.folder / "journal.jsonl"; raw = path.read_bytes()
        with self.assertRaises(JournalError):
            tx.journal.append("EXECUTE_COMMAND", {"command": "not executable"})
        self.assertEqual(path.read_bytes(), raw)

    def test_reordered_complete_records_rejected(self):
        tx = self.apply_replace(); path = tx.folder / "journal.jsonl"; lines = path.read_bytes().splitlines(keepends=True)
        lines[1], lines[2] = lines[2], lines[1]; path.write_bytes(b"".join(lines))
        with self.assertRaises(JournalError):
            tx.recover()

    def test_torn_tail_requires_explicit_repair_and_retains_raw_evidence(self):
        tx = self.prepare_replace()
        with self.assertRaises(SimulatedCrash):
            tx.simulate_apply({"original.txt": b"new bytes"}, crash("after_publish", 0))
        with (tx.folder / "journal.jsonl").open("ab") as stream:
            stream.write(b'{"partial":')
        damaged = (tx.folder / "journal.jsonl").read_bytes()
        self.assertTrue(tx.inspect()["torn_tail"])
        with self.assertRaises(JournalError):
            tx.recover()
        self.assertEqual(tx.recover(repair_torn_tail=True)["state"], "Recovered")
        self.assertEqual(next(tx.folder.glob("damaged-journal-*.bin")).read_bytes(), damaged)

    def test_journal_fsync_failure_does_not_claim_completed(self):
        tx = self.prepare_replace()
        with mock.patch("hf_payload.recovery.os.fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaises(OSError):
                tx.simulate_apply({"original.txt": b"new bytes"})
        self.assertEqual((self.target / "original.txt").read_bytes(), b"original bytes")

    def test_insufficient_backup_space(self):
        with mock.patch("hf_payload.recovery.shutil.disk_usage", return_value=SimpleNamespace(free=0)):
            with self.assertRaises(OSError):
                self.prepare_replace()
        self.assertEqual(list(self.area.sessions.iterdir()), [])
        self.assertEqual(snapshot(self.target / "original.txt"), self.original)

    def test_insufficient_recovery_space_preserves_current_file(self):
        tx = self.apply_replace()
        with mock.patch("hf_payload.recovery.shutil.disk_usage", return_value=SimpleNamespace(free=0)):
            self.assertEqual(tx.recover()["state"], "RecoveryRequired")
        self.assertEqual((self.target / "original.txt").read_bytes(), b"new bytes")
        self.assertEqual(tx.recover()["state"], "Recovered")

    def test_unsafe_paths_refused(self):
        for path in ("../escape", "C:/Games/file", "//server/share", "a:stream", "CON", "a/../b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.area.prepare([op(path, "create", b"x")])

    def test_case_insensitive_plan_collision(self):
        with self.assertRaises(SafetyError):
            self.area.prepare([op("new.txt", "create", b"x"), op("NEW.txt", "create", b"y")])

    def test_parent_child_plan_collision(self):
        with self.assertRaises(SafetyError):
            self.area.prepare([op("new", "create", b"x"), op("new/child", "create", b"y")])

    def test_existing_case_alias_is_not_treated_as_absent(self):
        with self.assertRaises(SafetyError):
            self.area.prepare([op("ORIGINAL.txt", "replace", b"x")])

    def test_nonexistent_parent_not_created_implicitly(self):
        with self.assertRaises((SafetyError, OSError)):
            self.area.prepare([op("missing/new.txt", "create", b"x")])
        self.assertFalse((self.target / "missing").exists())

    def test_outside_area_cannot_be_opened(self):
        with self.assertRaises(SafetyError):
            SyntheticArea(self.target)

    def test_second_session_not_allowed_even_after_recovery(self):
        self.prepare_replace().recover()
        with self.assertRaises(SafetyError):
            self.prepare_replace()

    def test_target_root_replacement_detected(self):
        tx = self.prepare_replace(); old = self.area.path / "old-target"
        self.target.rename(old); self.target.mkdir()
        with self.assertRaises(SafetyError):
            tx.recover()
        self.assertFalse((self.target / "original.txt").exists())

    def test_parent_directory_identity_replacement_detected(self):
        tx = self.area.prepare([op("protected/save.txt", "replace", b"new")])
        (self.target / "protected").rename(self.target / "old-protected"); (self.target / "protected").mkdir()
        with self.assertRaises(SafetyError):
            tx.simulate_apply({"protected/save.txt": b"new"})

    def test_hardlinked_preimage_refused(self):
        os.link(self.target / "original.txt", self.target / "alias.txt")
        with self.assertRaises(ValueError):
            self.prepare_replace()

    def test_static_reparse_point_guard(self):
        inode = (self.target / "original.txt").stat().st_ino
        from hf_payload import validator
        real = validator.linked
        with mock.patch("hf_payload.validator.linked", side_effect=lambda s: s.st_ino == inode or real(s)):
            with self.assertRaises(ValueError):
                self.prepare_replace()

    def test_foreign_transaction_identity_refused(self):
        tx = self.prepare_replace(); data = json.loads((tx.folder / "manifest.json").read_text())
        data["txid"] = "00000000-0000-0000-0000-000000000000"
        (tx.folder / "manifest.json").write_text(json.dumps(data))
        with self.assertRaises(SafetyError):
            tx.recover()

    def test_readonly_preimage_is_not_silently_repermissioned(self):
        path = self.target / "original.txt"; os.chmod(path, 0o444)
        if os.name != "nt":
            self.skipTest("Windows attribute refusal only; no POSIX ACL claim")
        with self.assertRaises(SafetyError):
            self.prepare_replace()

    def test_windows_named_stream_is_rejected(self):
        if os.name != "nt":
            self.skipTest("Windows streams only")
        Path(str(self.target / "original.txt") + ":note").write_bytes(b"private metadata")
        with self.assertRaises(SafetyError):
            self.prepare_replace()
        self.assertEqual(Path(str(self.target / "original.txt") + ":note").read_bytes(), b"private metadata")

    def test_real_windows_exclusive_lock_refused(self):
        if os.name != "nt":
            self.skipTest("Windows handle locking only")
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = create(str(self.target / "original.txt"), 0x80000000, 0, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with self.assertRaises(OSError):
                self.prepare_replace()
        finally:
            kernel.CloseHandle(handle)

    def test_real_windows_junction_escape_refused(self):
        if os.name != "nt":
            self.skipTest("Windows junctions only")
        import ctypes
        import struct
        from ctypes import wintypes
        outside = self.area.path / "junction-outside"; outside.mkdir(); (outside / "safe.txt").write_bytes(b"safe")
        link = self.target / "junction"; link.mkdir()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        ioctl = kernel.DeviceIoControl
        ioctl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        ioctl.restype = wintypes.BOOL
        handle = create(str(link), 0x40000000, 7, None, 3, 0x02200000, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        sub = ("\\??\\" + str(outside)).encode("utf-16-le"); printable = str(outside).encode("utf-16-le")
        payload = sub + b"\0\0" + printable + b"\0\0"
        data = struct.pack("<IHHHHHH", 0xA0000003, 8 + len(payload), 0, 0, len(sub), len(sub) + 2, len(printable)) + payload
        buffer = ctypes.create_string_buffer(data); returned = wintypes.DWORD()
        try:
            ok = ioctl(handle, 0x900A4, buffer, len(data), None, 0, ctypes.byref(returned), None)
            if not ok:
                self.fail("synthetic junction creation failed: " + str(ctypes.WinError(ctypes.get_last_error())))
        finally:
            kernel.CloseHandle(handle)
        try:
            with self.assertRaises(ValueError):
                self.area.prepare([op("junction/safe.txt", "delete")])
            self.assertEqual((outside / "safe.txt").read_bytes(), b"safe")
        finally:
            link.rmdir()  # Remove only this fixture's junction, never recurse through it.

    def test_real_directory_symlink_refused_if_os_permits(self):
        outside = self.area.path / "outside"; outside.mkdir(); (outside / "safe.txt").write_bytes(b"safe")
        link = self.target / "link"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except OSError as exc:
            self.skipTest("OS did not permit synthetic symlink: " + str(exc))
        try:
            with self.assertRaises(ValueError):
                self.area.prepare([op("link/safe.txt", "delete")])
            self.assertEqual((outside / "safe.txt").read_bytes(), b"safe")
        finally:
            link.unlink()


if __name__ == "__main__":
    unittest.main()
