"""Frozen command dispatcher; no development-interpreter fallback."""
import json
from pathlib import Path
import sys
from hf_payload.runtime_paths import initialize_portable, workspace
from hf_payload import startup_errors
import private_gui_install
import real_gui_install
import gui_install
import synthetic_install
import validate_ui_selection


def main():
    sys.argv[1:]=startup_errors.configure(sys.argv[1:])
    if sys.argv[1:] == ['--version']:
        print(json.dumps({'backend_version':'8B.2','scope':'synthetic-and-compatible-original-game','frozen':bool(getattr(sys,'frozen',False)),
              'private_game_mode':'technical compatibility plus exact-plan explicit consent',
              'python':sys.version,'state_root':str(workspace()),'module_origins':{
              name:str(Path(sys.modules[name].__file__)) for name in ('hf_payload.recovery','gui_install','synthetic_install')},
              'search_path':sys.path,'real_installation_allowed':False},indent=2))
        return 0
    initialize_portable()
    if len(sys.argv)<2 or sys.argv[1] not in ('gui','real-gui','private-gui','install','validate'):
        raise ValueError('expected gui, install or validate command')
    mode=sys.argv.pop(1)
    return {'private-gui':private_gui_install.main,'real-gui':real_gui_install.main,'gui':gui_install.main,'install':synthetic_install.main,'validate':validate_ui_selection.main}[mode]()


if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError) as exc:
        startup_errors.report(exc)
        print(json.dumps({'status':'RefusedUncertain','error':str(exc),'real_installation_allowed':False}))
        sys.exit(3)
