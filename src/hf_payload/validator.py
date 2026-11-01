"""Stdlib-only manifest verifier. Never loads payload code or writes to evidence."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys

MAX_MANIFEST = 8 * 1024 * 1024
MAX_ITEMS = 10000
HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
RESERVED = re.compile(r"(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I)


def safe_relative(value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError("relative path must be a nonempty bounded string")
    path = value.replace("\\", "/")
    if PureWindowsPath(path).drive or path.startswith("/"):
        raise ValueError("absolute, drive-relative and network paths are forbidden")
    parts = path.split("/")
    for part in parts:
        if (part in ("", ".", "..") or len(part) > 255 or part.endswith((".", " "))
                or RESERVED.fullmatch(part) or any(ord(c) < 32 or c in '<>:"|?*' for c in part)):
            raise ValueError("unsafe Windows filename or traversal")
    return "/".join(parts)


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def no_links(path):
    for item in (*reversed(path.parents), path):
        if linked(item.lstat()):
            raise ValueError("symlink/reparse point forbidden")


def stable_hash(path):
    no_links(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError("nonregular or hard-linked input forbidden")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        # On this Windows Python build lstat/fstat expose different ctime
        # semantics. Compare stable fields across APIs; retain ctime checks
        # within each API so real metadata changes still fail closed.
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_nlink)
        same_api = lambda s: identity(s) + (s.st_ctime_ns,)
        if identity(before) != identity(opened):
            raise ValueError("input changed before read")
        digest = hashlib.sha256()
        while block := stream.read(1024 * 1024):
            digest.update(block)
        if same_api(opened) != same_api(os.fstat(stream.fileno())):
            raise ValueError("input changed while hashing")
    no_links(path)
    if same_api(before) != same_api(path.lstat()):
        raise ValueError("input replaced while hashing")
    return before.st_size, digest.hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_manifest(path):
    if path.stat().st_size > MAX_MANIFEST:
        raise ValueError("manifest exceeds size limit")
    no_links(path)
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=unique_pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def validate(manifest, root):
    issues = []

    def issue(code, detail, kind="integrity"):
        issues.append({"kind": kind, "code": code, "detail": str(detail)})

    def fields(obj, names):
        if not isinstance(obj, dict) or set(obj) != set(names.split()):
            raise ValueError("object has missing/unknown fields: " + names)

    def text(value):
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 8192

    try:
        fields(manifest, "schema_version profile roots artifacts entries components readiness_gates")
        if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
            raise ValueError("unsupported schema version")
        if manifest["profile"] not in ("inspection", "synthetic"):
            raise ValueError("production profiles are not implemented")
        for name in ("roots", "artifacts", "entries", "components", "readiness_gates"):
            if not isinstance(manifest[name], list) or len(manifest[name]) > MAX_ITEMS:
                raise ValueError("invalid/oversized collection " + name)
        if not all(manifest[name] for name in ("roots", "artifacts", "entries", "components")):
            raise ValueError("required collection is empty")
        roots = [safe_relative(p) for p in manifest["roots"]]
        keys = [p.casefold() for p in roots]
        if len(set(keys)) != len(keys) or any(a != b and b.startswith(a + "/") for a in keys for b in keys):
            raise ValueError("duplicate/overlapping scan roots")
        root = Path(os.path.abspath(root))
        no_links(root)
        if not root.is_dir():
            raise ValueError("evidence root is not a directory")
        artifacts, paths = {}, {}
        for row in manifest["artifacts"]:
            fields(row, "id path size sha256 role")
            if not isinstance(row["id"], str) or not IDENTIFIER.fullmatch(row["id"]) or row["id"] in artifacts:
                raise ValueError("invalid/duplicate artifact ID")
            path = safe_relative(row["path"])
            if not any(path.casefold().startswith(k + "/") for k in keys):
                raise ValueError("artifact is outside declared scan roots")
            if path.casefold() in paths:
                raise ValueError("case-insensitive duplicate artifact path")
            if type(row["size"]) is not int or row["size"] < 0 or not isinstance(row["sha256"], str) or not HASH.fullmatch(row["sha256"]):
                raise ValueError("invalid size/SHA-256")
            if row["role"] not in ("payload-evidence", "reference-duplicate"):
                raise ValueError("invalid artifact role")
            artifacts[row["id"]] = row
            paths[path.casefold()] = path
        components = {}
        for row in manifest["components"]:
            fields(row, "id requires")
            if not isinstance(row["id"], str) or not IDENTIFIER.fullmatch(row["id"]) or row["id"] in components:
                raise ValueError("invalid/duplicate component ID")
            if not isinstance(row["requires"], list) or not all(isinstance(x, str) and IDENTIFIER.fullmatch(x) for x in row["requires"]):
                raise ValueError("invalid dependency list")
            components[row["id"]] = set(row["requires"])
        for name, deps in components.items():
            for dep in sorted(deps - components.keys()):
                issue("MISSING_DEPENDENCY", f"{name} requires {dep}", "readiness")
        remaining = {key: set(deps) & components.keys() for key, deps in components.items()}
        while remaining:
            leaves = {key for key, deps in remaining.items() if not deps}
            if not leaves:
                issue("DEPENDENCY_CYCLE", ", ".join(sorted(remaining)), "readiness")
                break
            remaining = {key: deps - leaves for key, deps in remaining.items() if key not in leaves}
        entries, destinations, used = set(), {}, set()
        for row in manifest["entries"]:
            fields(row, "id destination artifact component mapping authors license provenance historical_hint")
            if not isinstance(row["id"], str) or not IDENTIFIER.fullmatch(row["id"]) or row["id"] in entries:
                raise ValueError("invalid/duplicate entry ID")
            entries.add(row["id"])
            destination = safe_relative(row["destination"])
            if destination.casefold() in destinations:
                issue("DUPLICATE_DESTINATION", destination, "readiness")
                if destinations[destination.casefold()] != (row["component"], row["artifact"]):
                    issue("CONFLICTING_COMPONENT_MAPPING", destination, "readiness")
            destinations[destination.casefold()] = (row["component"], row["artifact"])
            if not isinstance(row["artifact"], str) or row["artifact"] not in artifacts:
                issue("MISSING_ARTIFACT_REFERENCE", row["id"])
            else:
                used.add(row["artifact"])
            if not isinstance(row["component"], str) or row["component"] not in components:
                issue("MISSING_COMPONENT", row["id"], "readiness")
            for name in ("mapping", "license", "provenance"):
                fields(row[name], "status evidence")
                allowed = {"resolved", "unresolved", "conflict"} if name == "mapping" else ({"approved", "unresolved", "denied"} if name == "license" else {"verified", "unverified"})
                if row[name]["status"] not in allowed or not text(row[name]["evidence"]):
                    raise ValueError("invalid review state/evidence")
                good = {"mapping": "resolved", "license": "approved", "provenance": "verified"}[name]
                if row[name]["status"] != good:
                    issue("UNRESOLVED_" + name.upper(), row["id"] + ": " + row[name]["evidence"], "readiness")
            if not text(row["authors"]) or row["authors"].strip().casefold() in ("unknown", "not established"):
                issue("UNKNOWN_AUTHOR", row["id"], "readiness")
            if not isinstance(row["historical_hint"], str) or len(row["historical_hint"]) > 8192:
                raise ValueError("invalid historical mapping hint")
        for aid, row in artifacts.items():
            if (aid in used) != (row["role"] == "payload-evidence"):
                issue("ARTIFACT_ROLE_CONFLICT", aid)
        for gate in manifest["readiness_gates"]:
            fields(gate, "id status evidence")
            if not text(gate["id"]) or gate["status"] not in ("qualified", "unresolved") or not text(gate["evidence"]):
                raise ValueError("invalid qualification gate")
            if gate["status"] != "qualified":
                issue("UNQUALIFIED_GATE", gate["id"] + ": " + gate["evidence"], "readiness")
        if manifest["profile"] == "inspection":
            issue("INSPECTION_ONLY", "Historical collision/ownership map is not a production selection plan", "readiness")
        # Inventory scan does not follow links. Only explicitly declared roots are inspected.
        found = set()
        for relative in roots:
            start = root.joinpath(*relative.split("/"))
            try:
                no_links(start)
                if not start.is_dir():
                    raise ValueError("scan root is missing/not a directory")
                pending = [start]
                while pending:
                    directory = pending.pop()
                    no_links(directory)
                    with os.scandir(directory) as listing:
                        for item in sorted(listing, key=lambda e: e.name.casefold()):
                            info = item.stat(follow_symlinks=False)
                            rel = Path(item.path).relative_to(root).as_posix()
                            if linked(info):
                                issue("UNSAFE_LINK", rel)
                            elif stat.S_ISDIR(info.st_mode):
                                pending.append(Path(item.path))
                            elif stat.S_ISREG(info.st_mode):
                                canonical = safe_relative(rel).casefold()
                                if canonical in found:
                                    issue("CASE_COLLISION", rel)
                                found.add(canonical)
                                if canonical not in paths:
                                    issue("UNEXPECTED_FILE", rel)
                            else:
                                issue("NONREGULAR_FILE", rel)
            except (OSError, ValueError) as exc:
                issue("SCAN_FAILURE", f"{relative}: {exc}")
        for aid, row in artifacts.items():
            rel = safe_relative(row["path"])
            path = root.joinpath(*rel.split("/"))
            try:
                size, digest = stable_hash(path)
                if size != row["size"]:
                    issue("SIZE_MISMATCH", rel)
                if digest != row["sha256"].lower():
                    issue("HASH_MISMATCH", rel)
            except FileNotFoundError:
                issue("MISSING_FILE", rel)
            except (OSError, ValueError) as exc:
                issue("FILE_READ_FAILURE", f"{rel}: {exc}")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        issue("INVALID_MANIFEST", exc)
    issues.sort(key=lambda x: (x["kind"], x["code"], x["detail"]))
    return {"schema_version": 1, "integrity_ok": not any(x["kind"] == "integrity" for x in issues),
            "readiness_ok": not issues, "installation_allowed": False, "release_authorized": False,
            "artifact_count": len(manifest.get("artifacts", [])) if isinstance(manifest, dict) else 0,
            "entry_count": len(manifest.get("entries", [])) if isinstance(manifest, dict) else 0,
            "issues": issues}


def markdown(result):
    counts = {}
    for item in result["issues"]:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    lines = ["# Payload validation", "", f"Integrity: {'PASS' if result['integrity_ok'] else 'FAIL'}",
             f"Manifest readiness: {'PASS' if result['readiness_ok'] else 'BLOCKED'}",
             "Installation and release authorization: always false in Phase 3A.",
             f"Artifacts: {result['artifact_count']}; entries: {result['entry_count']}", "",
             "## Issue counts", ""]
    lines += [f"- {code}: {count}" for code, count in sorted(counts.items())] or ["None."]
    lines += ["", "## First 50 findings", ""]
    lines += ["- " + html.escape(x["code"] + ": " + x["detail"]).replace("\n", " ") for x in result["issues"][:50]]
    return "\n".join(lines) + "\n"


def write_reports(result, report_dir, evidence_root, workspace):
    report_dir, workspace = Path(os.path.abspath(report_dir)), Path(os.path.abspath(workspace))
    out = workspace / "out"
    if not report_dir.is_relative_to(out) or report_dir == out:
        raise ValueError("reports must be in a new workspace/out subdirectory")
    for parent in (*reversed(report_dir.parents), report_dir):
        if parent.exists() or parent.is_symlink():
            no_links(parent)
    ev = Path(evidence_root).resolve()
    if report_dir.is_relative_to(ev) or ev.is_relative_to(report_dir):
        raise ValueError("reports may not overlap evidence")
    # Exclusive files: never overwrite prior reports or write to payload roots.
    report_dir.mkdir(parents=True, exist_ok=False)
    with (report_dir / "validation.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    with (report_dir / "validation.md").open("x", encoding="utf-8") as stream:
        stream.write(markdown(result))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate(load_manifest(args.manifest), args.evidence_root)
        if args.report_dir:
            write_reports(result, args.report_dir, args.evidence_root, Path(__file__).resolve().parents[2])
        print(json.dumps(result, indent=2))
        return 0 if result["readiness_ok"] else 2
    except (OSError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "installation_allowed": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
