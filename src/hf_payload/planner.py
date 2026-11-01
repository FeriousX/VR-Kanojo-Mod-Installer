"""Read-only synthetic operation planner. No installation authority or mutation API."""
from dataclasses import dataclass
import json
from .validator import safe_relative, IDENTIFIER, HASH, no_links
from .recovery import SyntheticArea, checked_area, SafetyError, snapshot, shape, digest, canonical, MAX_FILE, MAX_TOTAL


def identity(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise SafetyError("invalid owner/evidence identifier")
    return value


def expected(value):
    shape(value, "size sha256")
    if (type(value['size']) is not int or not 0 <= value['size'] <= MAX_FILE
            or not isinstance(value['sha256'], str) or not HASH.fullmatch(value['sha256'])):
        raise SafetyError("invalid expected file identity")
    return {'size': value['size'], 'sha256': value['sha256'].lower()}


def approval_key(request):
    """Bind consent to the complete request; changed source/preimage/owner invalidates it."""
    return digest(request)


@dataclass(frozen=True)
class Plan:
    document: str

    @property
    def sha256(self):
        return digest(json.loads(self.document))

    def as_dict(self):
        return json.loads(self.document)

    def recovery_operations(self):
        """Data adapter only. Does not prepare a transaction or authorize applying it."""
        return [{'path': r['destination'], 'action': 'protect' if r['action'] == 'preserve' else r['action'],
                 'post': r['post'] if r['action'] in ('create', 'replace') else None}
                for r in self.as_dict()['operations']]


def build_plan(area, requests, receipts, approvals, gates):
    """Inspect only an existing engine-created synthetic area; fail atomically on any refusal.

    Sources live in area/payload, destinations in area/target. Receipts and reviews
    are explicit synthetic declarations, not authenticated production credentials.
    """
    area = checked_area(area)
    shape(gates, 'profile compatibility licensing provenance mapping')
    if gates['profile'] != 'synthetic' or any(gates[k] is not True for k in gates if k != 'profile'):
        raise SafetyError('unresolved review gate or unsupported production profile')
    if not isinstance(requests, list) or not 1 <= len(requests) <= 1000:
        raise SafetyError('invalid operation collection')
    if not isinstance(receipts, list) or len(receipts) > 1000 or not isinstance(approvals, list):
        raise SafetyError('invalid evidence collections')
    if len(approvals) > 1000 or any(not isinstance(a, str) or not HASH.fullmatch(a) for a in approvals):
        raise SafetyError('invalid approval digest')
    owned = {}
    for row in receipts:
        shape(row, 'destination owner expected receipt')
        path = safe_relative(row['destination'])
        key = path.casefold()
        if key in owned:
            raise SafetyError('conflicting ownership receipts')
        owned[key] = {'owner': identity(row['owner']), 'expected': expected(row['expected']),
                      'receipt': identity(row['receipt'])}
    output, paths, total = [], [], 0
    for row in requests:
        shape(row, 'destination source action owner before after')
        dest = safe_relative(row['destination'])
        key = dest.casefold()
        if any(key == p or key.startswith(p + '/') or p.startswith(key + '/') for p in paths):
            raise SafetyError('case-insensitive or ancestor destination collision')
        paths.append(key)
        action = row['action']
        if action not in ('create', 'replace', 'preserve', 'delete'):
            raise SafetyError('unsupported file operation; directory operations forbidden')
        owner = identity(row['owner'])
        target = area.target / dest
        current = snapshot(target) if type(area) is SyntheticArea else area.inspect_destination(dest)
        prior = None if row['before'] is None else expected(row['before'])
        if (prior is None) != (not current['exists']):
            raise SafetyError('unexpected destination existence')
        if prior is not None and any(current[k] != prior[k] for k in prior):
            raise SafetyError('unexpected destination hash/size; re-review required')
        if action == 'create' and current['exists']:
            raise SafetyError('create requires absent destination')
        if action in ('replace', 'delete', 'preserve') and not current['exists']:
            raise SafetyError('operation requires an existing file')
        evidence = owned.get(key)
        if action in ('replace', 'delete'):
            if not evidence or evidence['owner'] != owner or evidence['expected'] != prior:
                raise SafetyError('unknown ownership or user-modified file; preserve instead')
        if action != 'preserve' and approval_key(row) not in approvals:
            raise SafetyError('missing exact operation approval')
        post, source, source_state = None, None, None
        if action in ('create', 'replace'):
            source = safe_relative(row['source'])
            no_links(area.path / 'payload')
            post = expected(row['after'])
            source_state = snapshot(area.path / 'payload' / source)
            if not source_state['exists'] or any(source_state[k] != post[k] for k in post):
                raise SafetyError('missing mapping or unexpected source hash')
            total += post['size']
        elif row['source'] is not None or row['after'] is not None:
            raise SafetyError('non-writing operation must not map payload')
        if total > MAX_TOTAL:
            raise SafetyError('aggregate payload bound exceeded')
        output.append({'destination': dest, 'source': source, 'action': action, 'owner': owner,
                       'before': current, 'post': post, 'source_state': source_state,
                       'ownership': evidence, 'approval': None if action == 'preserve' else approval_key(row)})
    # Detect changes across the scan before returning a plan. No lock/probe/journal writes.
    checked_area(area)
    for r in output:
        if (snapshot(area.target / r['destination']) if type(area) is SyntheticArea else area.inspect_destination(r['destination'])) != r['before']:
            raise SafetyError('destination changed during planning')
        if r['source'] and snapshot(area.path / 'payload' / r['source']) != r['source_state']:
            raise SafetyError('source changed during planning')
    return Plan(canonical({'schema': 1, 'scope': 'synthetic-only', 'area': area.path.name,
                           'target_id': area.marker['target_id'], 'gates': gates,
                           'installation_allowed': False, 'operations': output}).decode())
