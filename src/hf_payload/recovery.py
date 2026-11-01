"""Synthetic-only backup/journal/recovery core. No production installation API."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import uuid

from .validator import HASH, linked, no_links, safe_relative, stable_hash, unique_pairs
from .runtime_paths import workspace

WORKSPACE = workspace()
BASE = WORKSPACE / "out" / "synthetic"
RESERVE = 1024 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
STATES = {None: {"Prepared"}, "Prepared": {"BackedUp", "RecoveryRequired"},
          "BackedUp": {"Applying", "RecoveryRequired"}, "Applying": {"Completed", "RecoveryRequired"},
          "Completed": {"RecoveryRequired"}, "RecoveryRequired": {"RecoveryRequired", "Recovered"},
          "Recovered": {"RecoveryRequired"}}


class SafetyError(ValueError):
    pass


class JournalError(SafetyError):
    pass


class SimulatedCrash(BaseException):
    """Test-only interruption; deliberately bypasses ordinary error handling."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def shape(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise SafetyError("missing/unknown schema fields")


def identifier(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise SafetyError("invalid transaction/area ID")
    return value


def file_id(path):
    no_links(path)
    info = path.stat()
    return [info.st_dev, info.st_ino]


def present(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if linked(info):
        raise SafetyError("symlink/reparse point forbidden")
    no_links(path)
    return True


def exclusive_bytes(path, data):
    no_links(path.parent)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def read_json(path):
    no_links(path)
    if path.stat().st_size > MAX_JSON or path.stat().st_nlink != 1:
        raise SafetyError("unsafe/oversized JSON file")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(SafetyError("invalid number")))
    except (ValueError, RecursionError) as exc:
        raise SafetyError("invalid JSON") from exc


def reject_named_streams(path):
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    class StreamData(ctypes.Structure):
        _fields_ = [("size", ctypes.c_longlong), ("name", wintypes.WCHAR * 296)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    first, following, close = kernel.FindFirstStreamW, kernel.FindNextStreamW, kernel.FindClose
    first.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    following.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]; following.restype = wintypes.BOOL
    close.argtypes = [wintypes.HANDLE]; close.restype = wintypes.BOOL
    data = StreamData(); handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() == 38:  # ERROR_HANDLE_EOF
            return
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        while True:
            if data.name != "::$DATA":
                raise SafetyError("named streams are unsupported; refusing lossy backup")
            if not following(handle, ctypes.byref(data)):
                if ctypes.get_last_error() != 38:
                    raise ctypes.WinError(ctypes.get_last_error())
                break
    finally:
        close(handle)


def safe_existing(path):
    no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SafetyError("not a single-link regular file")
    # Synthetic metadata contract excludes read-only, encrypted, compressed,
    # sparse, reparse, hidden/system and other special Windows attributes.
    if getattr(info, "st_file_attributes", 0) & ~(0x20 | 0x80):
        raise SafetyError("unsupported Windows attributes")
    if info.st_size > MAX_FILE:
        raise SafetyError("synthetic file limit exceeded")
    reject_named_streams(path)
    return info


def snapshot(path):
    no_links(path.parent)
    try:
        info = safe_existing(path)
    except FileNotFoundError:
        return {"exists": False}
    size, sha = stable_hash(path)
    after = path.stat()
    if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise SafetyError("file changed during snapshot")
    return {"exists": True, "sha256": sha, "size": size, "file_id": [info.st_dev, info.st_ino],
            "mtime_ns": info.st_mtime_ns, "mode": stat.S_IMODE(info.st_mode)}


def content_matches(state, before):
    return state == before if not before["exists"] else (
        state["exists"] and all(state[k] == before[k] for k in ("sha256", "size", "mtime_ns", "mode")))


def copy_verified(source, destination, sha, size):
    safe_existing(source)
    if stable_hash(source) != (size, sha):
        raise SafetyError("source hash changed")
    no_links(destination.parent)
    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    if stable_hash(source) != (size, sha) or stable_hash(destination) != (size, sha):
        raise SafetyError("backup/stage verification failed")


def check_space(path, amount):
    if shutil.disk_usage(path).free < amount + RESERVE:
        raise OSError("insufficient free space including recovery reserve")


class Journal:
    """Hash-chained, flushed JSONL. A torn last record is never silently ignored."""
    def __init__(self, path, txid):
        self.path, self.txid = path, identifier(txid)

    def read(self, allow_tail=False, _raw=None):
        if _raw is None:
            if not present(self.path):
                return [], b""
            safe_existing(self.path)
            raw = self.path.read_bytes()
        else:
            raw = _raw
        if len(raw) > MAX_JSON:
            raise JournalError("journal exceeds size limit")
        records, previous, state = [], "0" * 64, None
        plan = None; gate = False; intents = set(); applied = set(); restored = set(); attempt = 0
        parts = raw.splitlines(keepends=True)
        tail = b""
        for index, line in enumerate(parts):
            if not line.endswith(b"\n"):
                if index != len(parts) - 1 or not allow_tail:
                    raise JournalError("torn journal tail; explicit repair required")
                tail = line
                break
            try:
                row = json.loads(line, object_pairs_hook=unique_pairs)
                shape(row, "schema txid seq previous event data hash")
                claimed = row["hash"]
                unsigned = {k: v for k, v in row.items() if k != "hash"}
                if (type(row["schema"]) is not int or row["schema"] != 1 or row["txid"] != self.txid
                        or type(row["seq"]) is not int or row["seq"] != len(records)
                        or row["previous"] != previous or claimed != digest(unsigned)):
                    raise JournalError("journal hash/sequence/identity mismatch")
                if row["event"] == "STATE":
                    shape(row["data"], "state")
                    next_state = row["data"]["state"]
                    if next_state not in STATES.get(state, set()):
                        raise JournalError("illegal state transition")
                    if next_state == "BackedUp" and not gate:
                        raise JournalError("BackedUp without backup gate")
                    if next_state == "Completed" and (plan is None or applied != set(plan["mutating_ops"])):
                        raise JournalError("Completed with pending operations")
                    if next_state == "Recovered" and (plan is None or restored != set(plan["mutating_ops"])):
                        raise JournalError("Recovered with pending restoration")
                    state = next_state
                elif row["event"] not in {"PLAN", "BACKUP_VERIFIED", "INTENT", "APPLIED", "ERROR", "RECOVERY_ATTEMPT",
                                            "RESTORE_INTENT", "RESTORED", "TAIL_REPAIRED"}:
                    raise JournalError("unknown event")
                elif state is None:
                    raise JournalError("event before Prepared")
                else:
                    event, data = row["event"], row["data"]
                    if event == "PLAN":
                        shape(data, "plan_sha256 operation_count mutating_ops")
                        if (state != "Prepared" or plan is not None or not isinstance(data["plan_sha256"], str)
                                or not HASH.fullmatch(data["plan_sha256"]) or type(data["operation_count"]) is not int
                                or not 1 <= data["operation_count"] <= 1000 or not isinstance(data["mutating_ops"], list)
                                or not all(type(i) is int and 0 <= i < data["operation_count"] for i in data["mutating_ops"])
                                or len(set(data["mutating_ops"])) != len(data["mutating_ops"])):
                            raise JournalError("invalid plan event")
                        plan = data
                    elif event == "BACKUP_VERIFIED":
                        shape(data, "manifest_sha256")
                        if state != "Prepared" or gate or plan is None or not isinstance(data["manifest_sha256"], str) or not HASH.fullmatch(data["manifest_sha256"]):
                            raise JournalError("invalid backup gate")
                        gate = True
                    elif event in ("INTENT", "APPLIED", "RESTORE_INTENT", "RESTORED"):
                        expected = {"INTENT": "op path stage_id stage_state", "APPLIED": "op post", "RESTORE_INTENT": "op stage_id", "RESTORED": "op result"}
                        shape(data, expected[event])
                        i = data["op"]
                        if plan is None or type(i) is not int or i not in plan["mutating_ops"]:
                            raise JournalError("event for unknown/nonmutating operation")
                        if event in ("INTENT", "APPLIED") and state != "Applying":
                            raise JournalError("apply event in wrong state")
                        if event in ("RESTORE_INTENT", "RESTORED") and state != "RecoveryRequired":
                            raise JournalError("recovery event in wrong state")
                        if event == "INTENT":
                            safe_relative(data["path"])
                            if i in intents:
                                raise JournalError("duplicate intent")
                            intents.add(i)
                            if data["stage_state"] is not None:
                                recorded_state(data["stage_state"])
                                if not data["stage_state"]["exists"] or data["stage_state"]["file_id"] != data["stage_id"]:
                                    raise JournalError("invalid staged postimage proof")
                            elif data["stage_id"] is not None:
                                raise JournalError("stage identity without state")
                        if event == "APPLIED":
                            if i not in intents or i in applied or not isinstance(data["post"], dict):
                                raise JournalError("applied event without unique intent")
                            recorded_state(data["post"])
                            applied.add(i)
                        if event == "RESTORED":
                            if data["result"] not in ("restored", "already-original", "removed-owned-new-file", "already-absent"):
                                raise JournalError("invalid restoration result")
                            restored.add(i)
                        if "stage_id" in data and data["stage_id"] is not None and (
                                not isinstance(data["stage_id"], list) or len(data["stage_id"]) != 2
                                or not all(type(x) is int and x >= 0 for x in data["stage_id"])):
                            raise JournalError("invalid stage identity")
                    elif event == "RECOVERY_ATTEMPT":
                        shape(data, "attempt")
                        if state != "RecoveryRequired" or type(data["attempt"]) is not int or data["attempt"] != attempt + 1:
                            raise JournalError("invalid recovery attempt")
                        attempt += 1; restored = set()
                    elif event == "ERROR":
                        shape(data, "operation op type message")
                        if not all(isinstance(data[k], str) and len(data[k]) <= 2048 for k in ("operation", "type", "message")):
                            raise JournalError("invalid error event")
                    elif event == "TAIL_REPAIRED":
                        shape(data, "evidence sha256 tail_bytes")
                        safe_relative(data["evidence"])
                        if not isinstance(data["sha256"], str) or not HASH.fullmatch(data["sha256"]) or type(data["tail_bytes"]) is not int or data["tail_bytes"] <= 0:
                            raise JournalError("invalid repair evidence")
                previous = claimed
                records.append(row)
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
                raise JournalError("corrupted complete journal record") from exc
        return records, tail

    def append(self, event, data):
        records, _ = self.read()
        row = {"schema": 1, "txid": self.txid, "seq": len(records),
               "previous": records[-1]["hash"] if records else "0" * 64, "event": event, "data": data}
        row["hash"] = digest(row)
        line = canonical(row) + b"\n"
        self.read(_raw=b"".join(canonical(r) + b"\n" for r in records) + line)
        if present(self.path):
            safe_existing(self.path)
        no_links(self.path.parent)
        with self.path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        self.read()  # Never report a durable successful event without read-back.

    def state(self, state):
        self.append("STATE", {"state": state})

    def repair_tail(self):
        records, tail = self.read(allow_tail=True)
        if not tail:
            return
        if not records:
            raise JournalError("no trusted complete prefix")
        raw = self.path.read_bytes()
        evidence = self.path.parent / ("damaged-journal-" + str(uuid.uuid4()) + ".bin")
        exclusive_bytes(evidence, raw)
        if evidence.read_bytes() != raw:
            raise JournalError("damaged journal preservation failed")
        replacement = self.path.parent / ("journal-repair-" + str(uuid.uuid4()) + ".tmp")
        exclusive_bytes(replacement, raw[:-len(tail)])
        os.replace(replacement, self.path)
        self.append("TAIL_REPAIRED", {"evidence": evidence.name, "sha256": hashlib.sha256(raw).hexdigest(), "tail_bytes": len(tail)})


def checked_area(area):
    # A path/marker alone cannot promote a synthetic area to an external target.
    if type(area) is SyntheticArea:
        return SyntheticArea(area.path)
    from .external_root import ExternalArea
    if type(area) is ExternalArea:
        area.revalidate()
        return area
    raise SafetyError("unsupported transaction area capability")


class SyntheticArea:
    manifest_kind = "synthetic-basic-v1"

    def inspect_destination(self, relative):
        return snapshot(self.target / safe_relative(relative))

    def prepare_directories(self, plan, fault):
        pass  # SyntheticArea keeps its existing parents-required restriction.

    @classmethod
    def create(cls):
        no_links(WORKSPACE)
        if not present(WORKSPACE / "out"):
            (WORKSPACE / "out").mkdir()
        if not present(BASE):
            BASE.mkdir()
        no_links(BASE)
        area = BASE / str(uuid.uuid4())
        area.mkdir()
        for name in ("target", "sessions"):
            (area / name).mkdir()
        exclusive_bytes(area / "synthetic.json", canonical({"schema": 1, "id": area.name, "kind": "synthetic-only",
                         "root_id": file_id(area), "target_id": file_id(area / "target"), "sessions_id": file_id(area / "sessions")}))
        return cls(area)

    def __init__(self, path):
        self.path = Path(os.path.abspath(path))
        if self.path.parent != BASE or not self.path.is_relative_to(BASE):
            raise SafetyError("only engine-created workspace/out/synthetic areas are allowed")
        identifier(self.path.name)
        no_links(self.path)
        marker = read_json(self.path / "synthetic.json")
        shape(marker, "schema id kind root_id target_id sessions_id")
        if (marker["schema"] != 1 or marker["id"] != self.path.name or marker["kind"] != "synthetic-only"
                or marker["root_id"] != file_id(self.path) or marker["target_id"] != file_id(self.path / "target")
                or marker["sessions_id"] != file_id(self.path / "sessions")):
            raise SafetyError("synthetic identity mismatch")
        self.marker = marker
        self.target, self.sessions = self.path / "target", self.path / "sessions"
        no_links(self.sessions)
        if file_id(self.target)[0] != file_id(self.sessions)[0]:
            raise SafetyError("synthetic target/session must share a volume")

    @contextmanager
    def lock(self):
        checked_area(self)
        path = self.path / ".engine.lock"
        if present(path):
            safe_existing(path)
        with path.open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0"); stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def destination(self, relative):
        relative = safe_relative(relative)
        current = self.target
        for part in relative.split("/"):
            no_links(current)
            if not current.is_dir():
                raise SafetyError("all destination parents must already exist")
            names = [x.name for x in current.iterdir() if x.name.casefold() == part.casefold()]
            if names and names != [part]:
                raise SafetyError("Windows case-insensitive alias/conflict")
            current = current / part
        if current.exists() or current.is_symlink():
            no_links(current)
        return current

    def prepare(self, operations, fault=lambda point, op: None):
        with self.lock():
            plan = validate_plan(operations)
            # Never start another transaction while one may have changed files.
            if any(self.sessions.iterdir()):
                raise SafetyError("one transaction per synthetic area; create a fresh area")
            before, parents, total = [], {}, 0
            for op in plan:
                target = self.destination(op["path"])
                state = snapshot(target)
                if op["action"] == "create" and state["exists"]:
                    raise SafetyError("create destination already exists")
                if op["action"] in ("replace", "delete") and not state["exists"]:
                    raise SafetyError("replace/delete requires an existing file")
                before.append(state)
                total += state.get("size", 0)
                for parent in (target.parent, *target.parent.parents):
                    if parent == self.target:
                        break
                    parents[parent.relative_to(self.target).as_posix()] = file_id(parent)
            if total > MAX_TOTAL:
                raise SafetyError("synthetic total limit exceeded")
            check_space(self.sessions, total * 2 + sum(x["post"]["size"] for x in plan if x["post"]) + 1024 * 1024)
            txid = str(uuid.uuid4()); folder = self.sessions / txid; folder.mkdir()
            for name in ("blobs", "stage"):
                (folder / name).mkdir()
            tx = Transaction(self, txid)
            tx.journal.state("Prepared")
            tx.journal.append("PLAN", {"plan_sha256": digest(plan), "operation_count": len(plan),
                                      "mutating_ops": [i for i, op in enumerate(plan) if op["action"] != "protect"]})
            try:
                for i, state in enumerate(before):
                    fault("before_backup", i)
                    if state["exists"]:
                        blob = folder / "blobs" / state["sha256"]
                        if not blob.exists():
                            copy_verified(self.destination(plan[i]["path"]), blob, state["sha256"], state["size"])
                        fault("after_backup_copy", i)
                        if stable_hash(blob) != (state["size"], state["sha256"]):
                            raise SafetyError("backup read-back failed")
                    if snapshot(self.destination(plan[i]["path"])) != state:
                        raise SafetyError("destination changed during backup")
                manifest = {"schema": 1, "kind": self.manifest_kind, "txid": txid, "area_id": self.marker["id"],
                            "target_id": self.marker["target_id"], "parents": parents, "plan": plan, "before": before}
                exclusive_bytes(folder / "manifest.json", canonical(manifest))
                fault("before_backup_gate", None)
                if any(snapshot(self.destination(op["path"])) != before[i] for i, op in enumerate(plan)):
                    raise SafetyError("preimage changed before backup gate")
                tx.journal.append("BACKUP_VERIFIED", {"manifest_sha256": digest(manifest)})
                tx.verify()
                tx.journal.state("BackedUp")
                return tx
            except Exception as exc:
                tx.error("backup", None, exc)
                tx.journal.state("RecoveryRequired")
                raise


    def inspect_sessions(self):
        results = []
        with self.lock():
            for folder in sorted(self.sessions.iterdir()):
                try:
                    no_links(folder)
                    results.append(Transaction(self, folder.name).inspect())
                except (ValueError, OSError) as exc:
                    results.append({"txid": folder.name, "state": "Unreadable", "interrupted": True,
                                    "error": type(exc).__name__ + ": " + str(exc)})
        return results


def validate_plan(operations):
    if not isinstance(operations, list) or not 1 <= len(operations) <= 1000:
        raise SafetyError("explicit nonempty bounded operation list required")
    result, seen = [], set()
    for op in operations:
        shape(op, "path action post")
        path = safe_relative(op["path"])
        key = path.casefold()
        if any(key == old or key.startswith(old + "/") or old.startswith(key + "/") for old in seen):
            raise SafetyError("duplicate/ancestor destination collision")
        seen.add(key)
        if op["action"] not in ("create", "replace", "delete", "protect"):
            raise SafetyError("unsupported action")
        post = op["post"]
        if op["action"] in ("create", "replace"):
            shape(post, "sha256 size")
            if not isinstance(post["sha256"], str) or not HASH.fullmatch(post["sha256"]) or type(post["size"]) is not int or not 0 <= post["size"] <= MAX_FILE:
                raise SafetyError("invalid planned postimage")
            post = {"sha256": post["sha256"].lower(), "size": post["size"]}
        elif post is not None:
            raise SafetyError("delete/protect cannot have a postimage")
        result.append({"path": path, "action": op["action"], "post": post})
    if sum(op["post"]["size"] for op in result if op["post"]) > MAX_TOTAL:
        raise SafetyError("synthetic postimage total limit exceeded")
    return result


def recorded_state(state):
    if not isinstance(state, dict) or type(state.get("exists")) is not bool:
        raise SafetyError("invalid recorded existence")
    shape(state, "exists sha256 size file_id mtime_ns mode" if state["exists"] else "exists")
    if state["exists"] and (not isinstance(state["sha256"], str) or not HASH.fullmatch(state["sha256"])
            or type(state["size"]) is not int or not 0 <= state["size"] <= MAX_FILE
            or type(state["mode"]) is not int or not 0 <= state["mode"] <= 0o777
            or type(state["mtime_ns"]) is not int or state["mtime_ns"] < 0
            or not isinstance(state["file_id"], list) or len(state["file_id"]) != 2
            or not all(type(x) is int and x >= 0 for x in state["file_id"])):
        raise SafetyError("invalid recorded metadata")


class Transaction:
    def __init__(self, area, txid):
        self.area, self.txid = area, identifier(txid)
        self.folder = area.sessions / txid
        no_links(self.folder)
        self.journal = Journal(self.folder / "journal.jsonl", txid)

    def error(self, operation, index, exc):
        self.journal.append("ERROR", {"operation": operation, "op": index, "type": type(exc).__name__, "message": str(exc)[:2048]})

    def inspect(self):
        records, tail = self.journal.read(allow_tail=True)
        state = next((r["data"]["state"] for r in reversed(records) if r["event"] == "STATE"), None)
        applied = sorted({r["data"]["op"] for r in records if r["event"] == "APPLIED"})
        restored = sorted({r["data"]["op"] for r in records if r["event"] == "RESTORED"})
        plan = next((r["data"] for r in records if r["event"] == "PLAN"), {})
        planned = plan.get("mutating_ops", [])
        return {"txid": self.txid, "state": state, "interrupted": bool(tail) or state in (None, "Prepared", "Applying", "RecoveryRequired"),
                "torn_tail": bool(tail), "applied": applied, "restored": restored,
                "pending": sorted(set(planned) - set(applied)), "recovery_pending": sorted(set(planned) - set(restored)),
                "backup_gate_recorded": any(r["event"] == "BACKUP_VERIFIED" for r in records),
                "errors": [r["data"] for r in records if r["event"] == "ERROR"]}

    def verify(self):
        checked_area(self.area)
        records, _ = self.journal.read()
        manifest = read_json(self.folder / "manifest.json")
        shape(manifest, "schema kind txid area_id target_id parents plan before")
        gates = [r for r in records if r["event"] == "BACKUP_VERIFIED"]
        if (manifest["schema"] != 1 or manifest["kind"] != self.area.manifest_kind or manifest["txid"] != self.txid
                or manifest["area_id"] != self.area.marker["id"] or manifest["target_id"] != file_id(self.area.target)
                or len(gates) != 1 or gates[0]["data"] != {"manifest_sha256": digest(manifest)}):
            raise SafetyError("backup gate/manifest identity mismatch")
        plan = validate_plan(manifest["plan"])
        plans = [r for r in records if r["event"] == "PLAN"]
        if len(plans) != 1 or plans[0]["data"] != {"plan_sha256": digest(plan), "operation_count": len(plan),
                                                 "mutating_ops": [i for i, op in enumerate(plan) if op["action"] != "protect"]}:
            raise SafetyError("plan digest mismatch")
        if not isinstance(manifest["before"], list) or len(manifest["before"]) != len(plan) or not isinstance(manifest["parents"], dict):
            raise SafetyError("invalid preimage/parent map")
        for parent, identity in manifest["parents"].items():
            path = self.area.target.joinpath(*safe_relative(parent).split("/"))
            if file_id(path) != identity:
                raise SafetyError("destination parent identity changed")
        for i, before in enumerate(manifest["before"]):
            self.area.destination(plan[i]["path"])
            recorded_state(before)
            if before["exists"]:
                if stable_hash(self.folder / "blobs" / before["sha256"]) != (before["size"], before["sha256"]):
                    raise SafetyError("missing/corrupted backup")
        return manifest

    def simulate_apply(self, postimages, fault=lambda point, op: None):
        """Test harness only: bytes supplied by synthetic fixtures, no HF payload API."""
        with self.area.lock():
            manifest = self.verify()
            if self.inspect()["state"] != "BackedUp":
                raise SafetyError("not ready to apply; no resume-apply shortcut")
            plan = manifest["plan"]
            try:
                for i, op in enumerate(plan):
                    if snapshot(self.area.destination(op["path"])) != manifest["before"][i]:
                        raise SafetyError("file modified after backup")
                    if op["post"]:
                        data = postimages.get(op["path"])
                        if not isinstance(data, bytes) or len(data) != op["post"]["size"] or hashlib.sha256(data).hexdigest() != op["post"]["sha256"]:
                            raise SafetyError("synthetic postimage mismatch")
                check_space(self.area.target, sum(x["post"]["size"] for x in plan if x["post"]) + 1024 * 1024)
                self.journal.state("Applying")
                for i, op in enumerate(plan):
                    if op["action"] == "protect":
                        continue
                    target = self.area.destination(op["path"])
                    if snapshot(target) != manifest["before"][i]:
                        raise SafetyError("destination changed before operation")
                    stage = self.folder / "stage" / (str(i) + ".new")
                    stage_id, stage_state = None, None
                    if op["post"]:
                        exclusive_bytes(stage, postimages[op["path"]])
                        if stable_hash(stage) != (op["post"]["size"], op["post"]["sha256"]):
                            raise SafetyError("stage verification failed")
                        stage_state = snapshot(stage); stage_id = stage_state["file_id"]
                    self.journal.append("INTENT", {"op": i, "path": op["path"], "stage_id": stage_id, "stage_state": stage_state})
                    fault("after_intent", i)
                    if snapshot(target) != manifest["before"][i]:
                        raise SafetyError("destination changed after intent")
                    if op["action"] == "delete":
                        target.unlink()
                    elif op["action"] == "create":
                        publish_new(stage, target)
                    else:
                        os.replace(stage, target)
                    fault("after_publish", i)
                    post = snapshot(target)
                    if not post_ok(post, op, stage_id) or (stage_state is not None and post != stage_state):
                        raise SafetyError("postimage verification failed")
                    self.journal.append("APPLIED", {"op": i, "post": post})
                    fault("after_applied", i)
                records, _ = self.journal.read()
                receipts = {r["data"]["op"]: r["data"]["post"] for r in records if r["event"] == "APPLIED"}
                for i, op in enumerate(plan):
                    expected = manifest["before"][i] if op["action"] == "protect" else receipts[i]
                    if snapshot(self.area.destination(op["path"])) != expected:
                        raise SafetyError("final synthetic apply reconciliation failed")
                self.journal.state("Completed")
            except Exception as exc:
                self.error("synthetic_apply", None, exc)
                self.journal.state("RecoveryRequired")
                raise

    def recover(self, repair_torn_tail=False, fault=lambda point, op: None):
        with self.area.lock():
            if repair_torn_tail:
                self.journal.repair_tail()
            try:
                manifest = self.verify()  # All backups validated before any restore.
            except Exception as exc:
                # Record refused attempts only if the journal itself is readable.
                # Never append to a corrupted/torn journal without explicit repair.
                records, _ = self.journal.read()
                self.journal.state("RecoveryRequired")
                self.journal.append("RECOVERY_ATTEMPT", {"attempt": 1 + sum(r["event"] == "RECOVERY_ATTEMPT" for r in records)})
                self.error("recovery_preflight", None, exc)
                raise
            records, _ = self.journal.read()
            plan, before = manifest["plan"], manifest["before"]
            intents, applied = {}, {}
            for row in records:
                if row["event"] in ("INTENT", "APPLIED", "RESTORED", "RESTORE_INTENT"):
                    i = row["data"].get("op")
                    if type(i) is not int or not 0 <= i < len(plan):
                        raise JournalError("invalid operation index")
                    if row["event"] == "INTENT":
                        shape(row["data"], "op path stage_id stage_state")
                        if i in intents or row["data"]["path"] != plan[i]["path"]:
                            raise JournalError("duplicate/changed intent")
                        intents[i] = row["data"]
                    if row["event"] == "APPLIED":
                        shape(row["data"], "op post")
                        if (i not in intents or not post_ok(row["data"]["post"], plan[i], intents[i]["stage_id"])
                                or (intents[i]["stage_state"] is not None and row["data"]["post"] != intents[i]["stage_state"])):
                            raise JournalError("invalid applied receipt")
                        applied[i] = row["data"]["post"]
            if self.inspect()["state"] == "Recovered" and all(op["action"] == "protect" or content_matches(snapshot(self.area.destination(op["path"])), before[i]) for i, op in enumerate(plan)):
                return {"state": "Recovered", "outcomes": [], "idempotent": True}
            self.journal.state("RecoveryRequired")
            self.journal.append("RECOVERY_ATTEMPT", {"attempt": 1 + sum(r["event"] == "RECOVERY_ATTEMPT" for r in records)})
            outcomes, failed = [], False
            for i in reversed(range(len(plan))):
                op = plan[i]
                if op["action"] == "protect":
                    outcomes.append({"op": i, "result": "snapshot-only-preserved"}); continue
                try:
                    target = self.area.destination(op["path"])
                    current = snapshot(target)
                    if content_matches(current, before[i]):
                        outcome = "already-original"
                    elif i not in intents:
                        raise SafetyError("unowned external change without intent")
                    elif current["exists"] and not (current == applied[i] if i in applied else current == intents[i]["stage_state"]):
                        raise SafetyError("user modification/uncertain ownership; preserved")
                    else:
                        check_space(self.area.target, before[i].get("size", 0) + 1024 * 1024)
                        fault("before_restore", i)
                        # Recheck before destructive work, never overwrite unknown data.
                        if snapshot(target) != current:
                            raise SafetyError("file changed during recovery")
                        if before[i]["exists"]:
                            stage = self.folder / "stage" / ("restore-" + str(uuid.uuid4()))
                            copy_verified(self.folder / "blobs" / before[i]["sha256"], stage, before[i]["sha256"], before[i]["size"])
                            os.chmod(stage, before[i]["mode"])
                            os.utime(stage, ns=(stage.stat().st_atime_ns, before[i]["mtime_ns"]))
                            self.journal.append("RESTORE_INTENT", {"op": i, "stage_id": file_id(stage)})
                            if snapshot(target) != current:
                                raise SafetyError("file changed before restore publication")
                            if current["exists"]:
                                os.replace(stage, target)
                            else:
                                publish_new(stage, target)
                            outcome = "restored"
                        elif current["exists"]:
                            self.journal.append("RESTORE_INTENT", {"op": i, "stage_id": None})
                            target.unlink()
                            outcome = "removed-owned-new-file"
                        else:
                            outcome = "already-absent"
                        fault("after_restore_publish", i)
                        if not content_matches(snapshot(target), before[i]):
                            raise SafetyError("restored bytes/metadata verification failed")
                    self.journal.append("RESTORED", {"op": i, "result": outcome})
                    outcomes.append({"op": i, "result": outcome})
                except Exception as exc:
                    failed = True
                    self.error("recovery", i, exc)
                    outcomes.append({"op": i, "result": "preserved-or-failed", "error": str(exc)})
            if not failed:
                for i, op in enumerate(plan):
                    if op["action"] != "protect":
                        try:
                            if not content_matches(snapshot(self.area.destination(op["path"])), before[i]):
                                raise SafetyError("final recovery reconciliation failed")
                        except Exception as exc:
                            failed = True
                            self.error("recovery_final_verification", i, exc)
                            outcomes.append({"op": i, "result": "preserved-or-failed", "error": str(exc)})
            if not failed:
                self.journal.state("Recovered")
            return {"state": "RecoveryRequired" if failed else "Recovered", "outcomes": outcomes, "idempotent": False}


def post_ok(state, op, stage_id):
    if op["action"] == "delete":
        return state == {"exists": False}
    return (isinstance(state, dict) and state.get("exists") is True and op["post"] is not None
            and state.get("sha256") == op["post"]["sha256"] and state.get("size") == op["post"]["size"]
            and state.get("file_id") == stage_id and stage_id is not None)


def publish_new(stage, target):
    if os.name == "nt":
        os.rename(stage, target)  # Windows rename fails rather than replacing an existing destination.
    else:
        os.link(stage, target)  # POSIX no-overwrite publication; crashes may leave a hardlink and refuse recovery.
        stage.unlink()
