"""Standalone bridge: prepare stdin JSON; execute with explicit digest; recover/status by UUID only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hf_payload import install_bridge
from hf_payload.validator import unique_pairs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare')
    for name in ('execute','recover','status'):
        command=sub.add_parser(name); command.add_argument('--id',required=True)
        if name=='execute': command.add_argument('--approve-plan',required=True)
    args=parser.parse_args()
    try:
        if args.command=='prepare':
            raw=sys.stdin.buffer.read(16385)
            if len(raw)>16384: raise ValueError('request exceeds 16 KiB')
            request=json.loads(raw,object_pairs_hook=unique_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
            result=install_bridge.prepare(request)
        elif args.command=='execute': result=install_bridge.execute(args.id,args.approve_plan)
        elif args.command=='recover': result=install_bridge.recover(args.id)
        else: result=install_bridge.status(args.id)
        result.update(schema_version=1,scope='synthetic-install-bridge')
        result.setdefault('percent',None)
        print(json.dumps(result,indent=2))
        return 0 if result['status'] in ('PreparedAwaitingConsent','CommittedSynthetic','Recovered') else 2
    except (ValueError,OSError,KeyError,TypeError,RecursionError) as exc:
        print(json.dumps({'schema_version':1,'scope':'synthetic-install-bridge','status':'RefusedUncertain','error':str(exc),'percent':None,
                          'real_installation_allowed':False,'summary':'No success is claimed. Preserve evidence and inspect/recover this fixture.'}))
        return 3


if __name__=='__main__': sys.exit(main())
