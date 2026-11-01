"""Bounded, exclusive diagnostic handoff before portable state can initialize."""
from pathlib import Path
import os,re,tempfile
from .validator import no_links
from .recovery import SafetyError,exclusive_bytes,present
_ERROR_FILE=None

def configure(arguments):
    global _ERROR_FILE
    _ERROR_FILE=None
    args=list(arguments)
    if '--startup-error-file' not in args:return args
    if args.count('--startup-error-file')!=1:raise SafetyError('duplicate startup error destination')
    i=args.index('--startup-error-file')
    if i+1==len(args):raise SafetyError('missing startup error destination')
    path=Path(os.path.abspath(args[i+1]));temp=Path(os.path.abspath(tempfile.gettempdir()))
    if not Path(args[i+1]).is_absolute() or temp not in path.parents or not re.fullmatch(r'hf-startup-[0-9a-f]{64}\.txt',path.name):
        raise SafetyError('startup diagnostics must use a unique temp file; arbitrary destinations forbidden')
    no_links(path.parent)
    if present(path):raise SafetyError('startup diagnostic already exists; retry with a new job')
    _ERROR_FILE=path
    return args[:i]+args[i+2:]

def report(error):
    if _ERROR_FILE is None:return
    message=('Backend refused: '+str(error)+'\nNo installation success is claimed. Keep transaction records if execution was already attempted.')[:4000]
    exclusive_bytes(_ERROR_FILE,message.encode('utf-8'))
