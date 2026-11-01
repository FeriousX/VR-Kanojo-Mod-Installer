"""Version-1 UI selection validation on authored synthetic text fixtures only."""
import hashlib
from .planner import build_plan, approval_key
from .recovery import SyntheticArea, SafetyError, canonical, digest, shape

CATALOG = {
    'core-framework': b'Authored synthetic core example. Not a runtime.\n',
    'configuration-tools': b'Authored synthetic settings example. Not a plugin.\n',
    'optional-utilities': b'Authored synthetic utilities example. Not a plugin.\n',
    'vrkanojo-desktop': b'Authored synthetic desktop selection. No plugin included.\n',
    'play-without-vr': b'Authored synthetic original desktop selection. No plugin included.\n'}
COMPONENTS = ('core-framework', 'configuration-tools', 'optional-utilities')
DESKTOP = ('vrkanojo-desktop', 'play-without-vr', 'neither')


def new_fixture():
    """Backend-owned fixture creation; no UI-supplied path or payload bytes."""
    area = SyntheticArea.create()
    (area.path / 'payload').mkdir()
    (area.target / 'proposal').mkdir()
    for key, data in CATALOG.items(): (area.path / 'payload' / (key + '.txt')).write_bytes(data)
    return area


def response_template():
    return {'schema_version': 1, 'scope': 'synthetic-validation-only', 'status': 'blocked',
                'request_digest': None, 'selected_components': [], 'desktop_mode': None,
                'demo_library': None, 'conflicts': [], 'blocked_operations': [], 'operations': [],
                'plan_digest': None, 'summary': '', 'installation_allowed': False,
                'execution_authorized': False, 'requires_separate_execution_consent': True}


def validate_selection(request, area, gates):
    response = response_template()
    proposed = []
    try:
        shape(request, 'schema_version action components desktop_mode demo_library')
        if type(request['schema_version']) is not int or request['schema_version'] != 1 or request['action'] != 'validate-selections':
            raise SafetyError('unsupported interface version/action')
        components = request['components']
        if (not isinstance(components, list) or len(components) > 3
                or any(not isinstance(c, str) or c not in COMPONENTS for c in components)
                or len(set(components)) != len(components)):
            raise SafetyError('invalid, unknown or duplicate component selection')
        if not isinstance(request['desktop_mode'], str) or request['desktop_mode'] not in DESKTOP:
            raise SafetyError('desktop_mode must select exactly one option')
        if request['demo_library'] not in ('demo-a', 'demo-b'):
            raise SafetyError('only fixed demo libraries are accepted; paths are forbidden')
        response.update(request_digest=digest(request), selected_components=[c for c in COMPONENTS if c in components],
                        desktop_mode=request['desktop_mode'], demo_library=request['demo_library'])
        selected = response['selected_components'] + ([] if request['desktop_mode'] == 'neither' else [request['desktop_mode']])
        for key in selected:
            data = CATALOG[key]
            proposed.append({'destination': 'proposal/' + key + '.txt', 'source': key + '.txt',
                             'action': 'create', 'owner': 'ui-synthetic-fixture', 'before': None,
                             'after': {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}})
        area = SyntheticArea(area.path)
        # The fixtures model dependency/conflict policies, never real payload readiness.
        if any(c in components for c in ('configuration-tools', 'optional-utilities')) or request['desktop_mode'] != 'neither':
            if 'core-framework' not in components: raise SafetyError('selected options require core-framework in this fixture catalog')
        existing = {key for key in DESKTOP[:2] if (area.target / 'proposal' / (key + '.txt')).exists()}
        if len(existing) > 1 or (existing and request['desktop_mode'] != 'neither' and request['desktop_mode'] not in existing):
            raise SafetyError('conflicting desktop fixture selections; preserve existing files')
        # Build even no-op selections' gates explicitly; no empty-plan bypass of review gates.
        shape(gates, 'profile compatibility licensing provenance mapping')
        if gates['profile'] != 'synthetic' or any(gates[k] is not True for k in gates if k != 'profile'):
            raise SafetyError('synthetic compatibility/licensing/provenance/mapping gates unresolved')
        if proposed:
            plan = build_plan(area, proposed, [], [approval_key(r) for r in proposed], gates)
            response['plan_digest'] = plan.sha256
            response['operations'] = [{'destination':r['destination'], 'action':r['action']} for r in proposed]
        response['status'] = 'valid'
        response['summary'] = ('Validated synthetic choices: ' + (', '.join(selected) if selected else 'none') +
                               '. ' + str(len(proposed)) + ' proposed text-file additions; no files installed. Separate execution consent is required.')
    except (ValueError, OSError) as exc:
        response['conflicts'] = [{'code':'VALIDATION_BLOCKED', 'message':str(exc)}]
        response['blocked_operations'] = [{'destination':r['destination'], 'reason':str(exc)} for r in proposed]
        response['summary'] = 'Validation blocked: ' + str(exc) + '. No installation is authorized.'
    return response
