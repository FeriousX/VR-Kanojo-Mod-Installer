import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

from hf_payload.validator import load_manifest, main, safe_relative, validate, write_reports

WORKSPACE = Path(__file__).resolve().parents[1]


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        scratch = WORKSPACE / "out" / "test-fixtures"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-", dir=scratch)
        self.work = Path(self.temp.name)
        self.root = self.work / "evidence"
        (self.root / "payload").mkdir(parents=True)
        self.file = self.root / "payload" / "sample.txt"
        self.file.write_bytes(b"synthetic fixture, not a game assembly\n")
        self.m = {"schema_version": 1, "profile": "synthetic", "roots": ["payload"],
                  "artifacts": [{"id": "a1", "path": "payload/sample.txt", "size": self.file.stat().st_size,
                                 "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest(), "role": "payload-evidence"}],
                  "components": [{"id": "core", "requires": []}], "readiness_gates": [],
                  "entries": [{"id": "e1", "destination": "Data/sample.txt", "artifact": "a1", "component": "core",
                               "mapping": {"status": "resolved", "evidence": "synthetic test mapping"},
                               "authors": "Synthetic test author", "license": {"status": "approved", "evidence": "test-owned fixture"},
                               "provenance": {"status": "verified", "evidence": "created by this test"}, "historical_hint": ""}]}

    def tearDown(self):
        self.temp.cleanup()

    def codes(self, m=None):
        return {x["code"] for x in validate(self.m if m is None else m, self.root)["issues"]}

    def test_valid_manifest(self):
        result = validate(self.m, self.root)
        self.assertTrue(result["integrity_ok"] and result["readiness_ok"])
        self.assertFalse(result["installation_allowed"] or result["release_authorized"])

    def test_missing_file(self):
        self.file.unlink()
        self.assertIn("MISSING_FILE", self.codes())

    def test_incorrect_hash(self):
        self.m["artifacts"][0]["sha256"] = "0" * 64
        self.assertIn("HASH_MISMATCH", self.codes())

    def test_size_mismatch(self):
        self.m["artifacts"][0]["size"] += 1
        self.assertIn("SIZE_MISMATCH", self.codes())

    def test_unexpected_file(self):
        (self.file.parent / "extra.txt").write_text("not declared")
        self.assertIn("UNEXPECTED_FILE", self.codes())

    def test_duplicate_destinations_case_insensitive(self):
        row = copy.deepcopy(self.m["entries"][0]); row["id"] = "e2"; row["destination"] = "data/SAMPLE.txt"
        self.m["entries"].append(row)
        self.assertIn("DUPLICATE_DESTINATION", self.codes())

    def test_different_components_competing_for_one_destination(self):
        row = copy.deepcopy(self.m["entries"][0]); row.update(id="e2", component="other")
        self.m["components"].append({"id": "other", "requires": []})
        self.m["entries"].append(row)
        self.assertIn("CONFLICTING_COMPONENT_MAPPING", self.codes())

    def test_unsafe_windows_paths(self):
        for path in ("../escape", "a/../b", "C:/file", "C:file", "//server/share", "a:stream", "a//b",
                     "NUL.txt", "COM1", "LPT¹.log", "a. ", "a.", "a/*", "a/?", "a/./b", "a\x00b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)

    def test_ordinary_spaces_unicode_and_shell_characters_are_data(self):
        self.assertEqual(safe_relative("My Mods/日本語 & 100%.txt"), "My Mods/日本語 & 100%.txt")

    def test_artifact_outside_scan_roots(self):
        self.m["artifacts"][0]["path"] = "outside/sample.txt"
        self.assertIn("INVALID_MANIFEST", self.codes())

    def test_unsafe_destination(self):
        self.m["entries"][0]["destination"] = "../outside"
        self.assertIn("INVALID_MANIFEST", self.codes())

    def test_component_mapping_conflict(self):
        self.m["entries"][0]["mapping"]["status"] = "conflict"
        self.assertIn("UNRESOLVED_MAPPING", self.codes())

    def test_unresolved_mapping(self):
        self.m["entries"][0]["mapping"]["status"] = "unresolved"
        self.assertIn("UNRESOLVED_MAPPING", self.codes())

    def test_unknown_provenance(self):
        self.m["entries"][0]["provenance"]["status"] = "unverified"
        self.assertIn("UNRESOLVED_PROVENANCE", self.codes())

    def test_unapproved_license(self):
        for state in ("unresolved", "denied"):
            self.m["entries"][0]["license"]["status"] = state
            self.assertIn("UNRESOLVED_LICENSE", self.codes())

    def test_unknown_author(self):
        self.m["entries"][0]["authors"] = "Unknown"
        self.assertIn("UNKNOWN_AUTHOR", self.codes())

    def test_missing_dependency(self):
        self.m["components"][0]["requires"] = ["missing"]
        self.assertIn("MISSING_DEPENDENCY", self.codes())

    def test_missing_component(self):
        self.m["entries"][0]["component"] = "missing"
        self.assertIn("MISSING_COMPONENT", self.codes())

    def test_dependency_cycle(self):
        self.m["components"] = [{"id": "core", "requires": ["other"]}, {"id": "other", "requires": ["core"]}]
        self.assertIn("DEPENDENCY_CYCLE", self.codes())

    def test_qualification_gate(self):
        self.m["readiness_gates"] = [{"id": "compiler", "status": "unresolved", "evidence": "not qualified"}]
        self.assertIn("UNQUALIFIED_GATE", self.codes())

    def test_inspection_is_not_a_production_profile(self):
        self.m["profile"] = "inspection"
        result = validate(self.m, self.root)
        self.assertTrue(result["integrity_ok"])
        self.assertFalse(result["readiness_ok"])

    def test_unknown_fields_and_boolean_size_rejected(self):
        self.m["artifacts"][0]["size"] = True
        self.assertIn("INVALID_MANIFEST", self.codes())
        self.m["extra"] = "must not be ignored"
        self.assertIn("INVALID_MANIFEST", self.codes())

    def test_duplicate_json_keys_rejected(self):
        path = self.work / "duplicate.json"; path.write_text('{"schema_version":1,"schema_version":2}')
        with self.assertRaises(ValueError):
            load_manifest(path)

    def test_duplicate_artifact_paths(self):
        row = copy.deepcopy(self.m["artifacts"][0]); row["id"] = "a2"
        self.m["artifacts"].append(row)
        self.assertIn("INVALID_MANIFEST", self.codes())

    def test_numeric_artifact_id_is_not_coerced_to_text(self):
        self.m["artifacts"][0]["id"] = 123
        self.assertIn("INVALID_MANIFEST", self.codes())

    def test_hardlink_rejected(self):
        link = self.work / "alias.txt"
        os.link(self.file, link)
        self.assertIn("FILE_READ_FAILURE", self.codes())

    def test_reparse_detection_without_symlink_privilege(self):
        inode = self.file.parent.stat().st_ino
        with mock.patch("hf_payload.validator.linked", side_effect=lambda info: info.st_ino == inode):
            self.assertIn("SCAN_FAILURE", self.codes())

    def test_reference_duplicate_explicitly_declared(self):
        duplicate = self.file.parent / "reference.txt"; duplicate.write_bytes(self.file.read_bytes())
        row = copy.deepcopy(self.m["artifacts"][0]); row.update(id="a2", path="payload/reference.txt", role="reference-duplicate")
        self.m["artifacts"].append(row)
        self.assertFalse(self.codes())

    def test_unreferenced_payload_is_not_silently_accepted(self):
        self.m["artifacts"][0]["role"] = "reference-duplicate"
        self.assertIn("ARTIFACT_ROLE_CONFLICT", self.codes())

    def test_read_only_files_hashes_names_and_metadata_unchanged(self):
        manifest = self.work / "manifest.json"; manifest.write_text(json.dumps(self.m))
        snapshot = lambda: {str(p): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_size) for p in self.root.rglob("*") if p.is_file()}
        before, manifest_bytes = snapshot(), manifest.read_bytes()
        with mock.patch("builtins.print"):
            self.assertEqual(main(["--manifest", str(manifest), "--evidence-root", str(self.root)]), 0)
        self.assertEqual(snapshot(), before)
        self.assertEqual(manifest.read_bytes(), manifest_bytes)

    def test_deterministic_results(self):
        self.assertEqual(validate(self.m, self.root), validate(self.m, self.root))

    def test_windows_cross_api_ctime_difference_is_not_a_changed_file(self):
        s = self.file.stat()
        values = {name: getattr(s, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink", "st_ctime_ns")}
        values["st_ctime_ns"] += 100
        handle = SimpleNamespace(**values)
        with mock.patch("hf_payload.validator.os.fstat", return_value=handle):
            self.assertTrue(validate(self.m, self.root)["integrity_ok"])

    def test_handle_metadata_change_during_read_is_rejected(self):
        s = self.file.stat()
        values = {name: getattr(s, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink", "st_ctime_ns")}
        first = SimpleNamespace(**values)
        values["st_ctime_ns"] += 1
        changed = SimpleNamespace(**values)
        with mock.patch("hf_payload.validator.os.fstat", side_effect=[first, changed]):
            self.assertIn("FILE_READ_FAILURE", self.codes())

    def test_report_cannot_write_into_evidence(self):
        with self.assertRaises(ValueError):
            write_reports(validate(self.m, self.root), self.root / "out", self.root, self.work)

    def test_reports_do_not_overwrite_and_keep_payload_unchanged(self):
        result = validate(self.m, self.root); output = self.work / "out" / "report"
        before = self.file.read_bytes()
        write_reports(result, output, self.root, self.work)
        self.assertTrue((output / "validation.md").is_file())
        with self.assertRaises(FileExistsError):
            write_reports(result, output, self.root, self.work)
        self.assertEqual(self.file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
