"""Fixed-path development transport for the real selection adapter. Never executes proposals."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hf_payload.ui_adapter import new_fixture, validate_selection, response_template, COMPONENTS, DESKTOP
from hf_payload.recovery import canonical, digest, exclusive_bytes
from hf_payload.validator import no_links

WORKSPACE = Path(__file__).resolve().parents[1]


def request_for(mask, desktop, library):
    if type(mask) is not int or not 0 <= mask <= 7 or desktop not in DESKTOP or library not in ('demo-a','demo-b'):
        raise ValueError('invalid selection arguments')
    return dict(schema_version=1,action='validate-selections',components=[c for i,c in enumerate(COMPONENTS) if mask & (1<<i)],
                desktop_mode=desktop,demo_library=library)


def projection(result, request, request_id, mask):
    required = set(response_template())
    if not isinstance(result, dict) or not required <= result.keys() or not result.keys() <= required | {'fixture_id'}:
        raise ValueError('missing or unexpected adapter response fields')
    if not isinstance(result['summary'], str): raise ValueError('summary must be text')
    for field in ('selected_components', 'operations', 'conflicts', 'blocked_operations'):
        if not isinstance(result[field], list) or len(result[field]) > 30:
            raise ValueError('invalid response collection: ' + field)
    if any(not isinstance(c, str) for c in result['selected_components']): raise ValueError('invalid component types')
    for field, keys in (('operations', ('action','destination')), ('conflicts', ('code','message')),
                        ('blocked_operations', ('destination','reason'))):
        for row in result[field]:
            if not isinstance(row, dict) or set(row) != set(keys) or any(not isinstance(row[k], str) for k in keys):
                raise ValueError('invalid display record: ' + field)
    if (type(result['schema_version']) is not int or result['schema_version'] != 1 or result['scope'] != 'synthetic-validation-only'
            or result['status'] not in ('valid','blocked') or result['request_digest'] != digest(request)
            or result['installation_allowed'] is not False or result['execution_authorized'] is not False
            or result['selected_components'] != request['components'] or result['desktop_mode'] != request['desktop_mode']
            or result['demo_library'] != request['demo_library']):
        raise ValueError('malformed or stale adapter response')
    lines = [result['summary'], '', 'Components: ' + (', '.join(result['selected_components']) or 'none'),
             'Desktop mode: ' + result['desktop_mode'], 'Demo library: ' + result['demo_library'], '',
             'PLANNER-VALIDATED SYNTHETIC PROPOSALS (not execution approval)']
    lines += [r['action'] + ': ' + r['destination'] for r in result['operations']]
    lines += ['BLOCKED: ' + r['message'] for r in result['conflicts']]
    lines += ['Blocked proposal: ' + r['destination'] + ' - ' + r['reason'] for r in result['blocked_operations']]
    if len(lines) > 30 or any(len(s) > 2000 or '\n' in s or '\r' in s for s in lines):
        raise ValueError('response display bounds exceeded')
    fields = dict(protocol='1',scope='synthetic-validation-only',request_id=request_id,status=result['status'],
                  binding=f"{mask}|{request['desktop_mode']}|{request['demo_library']}",
                  installation_allowed='0',execution_authorized='0',count=str(len(lines)))
    fields.update({'line'+str(i):line for i,line in enumerate(lines)})
    return fields


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',required=True); parser.add_argument('--mask',type=int,required=True)
    parser.add_argument('--desktop',choices=DESKTOP,required=True)
    parser.add_argument('--library',choices=('demo-a','demo-b'),required=True)
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.id): parser.error('invalid request ID')
    request=request_for(args.mask,args.desktop,args.library)
    no_links(WORKSPACE/'out')
    exchange=WORKSPACE/'out'/'ui-exchange'; exchange.mkdir(exist_ok=True); no_links(exchange)
    folder=exchange/args.id; folder.mkdir(exist_ok=False); no_links(folder)
    exclusive_bytes(folder/'request.json',canonical(request))
    area=new_fixture()
    result=validate_selection(request,area,dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True))
    result['fixture_id']=area.path.name
    fields=projection(result,request,args.id,args.mask)
    raw=canonical(result); exclusive_bytes(folder/'response.json',raw)
    fields['response_sha256']=hashlib.sha256(raw).hexdigest()
    # ASCII-only display projection keeps Inno's native INI reader independent of JSON parsing.
    config=configparser.ConfigParser(interpolation=None); config['validation']=fields
    import io
    stream=io.StringIO(); config.write(stream)
    exclusive_bytes(folder/'response.ini',stream.getvalue().encode('ascii'))
    return 0 if result['status']=='valid' else 2


if __name__=='__main__': sys.exit(main())
