"""Private wizard transport; target authorization lives in the pinned backend policy."""
import argparse,sys
import gui_install as gui
from hf_payload import private_game_bridge as bridge

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='action',required=True)
    prepare=commands.add_parser('prepare');prepare.add_argument('--target',required=True);prepare.add_argument('--disposable-copy',action='store_true',help=argparse.SUPPRESS)
    prepare.add_argument('--mask',type=int,required=True);prepare.add_argument('--desktop',required=True)
    for name in ('prepare','run','recover'):
        p=prepare if name=='prepare' else commands.add_parser(name);p.add_argument('--job',required=True)
        if name=='run':p.add_argument('--approve-plan',required=True)
    args=parser.parse_args()
    previous=(gui.bridge,gui.request_for,gui.TRANSPORT_SCOPE,gui.REAL_ALLOWED)
    gui.bridge,gui.request_for,gui.TRANSPORT_SCOPE,gui.REAL_ALLOWED=bridge,bridge.request_for,'private-game-gui-v1','1'
    try:
        if args.action=='prepare':gui.prepare_job(args.job,args.mask,args.desktop,args.target)
        else:gui.run_job(args.job,getattr(args,'approve_plan',None),recover=args.action=='recover')
        return 0
    except Exception as exc:
        from hf_payload import startup_errors
        startup_errors.report(exc)
        print('Private backend refused: '+str(exc),file=sys.stderr);return 3
    finally:gui.bridge,gui.request_for,gui.TRANSPORT_SCOPE,gui.REAL_ALLOWED=previous

if __name__=='__main__':raise SystemExit(main())
