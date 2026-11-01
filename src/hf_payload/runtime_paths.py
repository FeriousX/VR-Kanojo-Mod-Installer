"""Source workspace or explicitly marked portable synthetic state, never extraction storage."""
from pathlib import Path
import sys


def user_local_appdata():
    """Resolve the Windows per-user known folder, not a UI/env-supplied target."""
    import ctypes,os
    if os.name!='nt':raise ValueError('Persistent Windows backend requires Windows')
    shell=ctypes.WinDLL('shell32',use_last_error=True)
    buffer=ctypes.create_unicode_buffer(32768)
    call=shell.SHGetFolderPathW
    call.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint,ctypes.c_wchar_p]
    call.restype=ctypes.c_long
    if call(None,0x1c,None,0,buffer)!=0:raise ValueError('Cannot resolve per-user Local AppData; no state created')
    return Path(buffer.value)


def persistent_profile():
    if not getattr(sys,'frozen',False):return None
    try:
        import backend_profile
    except ImportError:return None  # Legacy portable backend compatibility only.
    return backend_profile.STATE_PARTS


def workspace():
    if getattr(sys,'frozen',False):
        parts=persistent_profile()
        if parts is not None:
            if type(parts) is not tuple or any(type(p) is not str or not p or p in ('.','..') or any(c in p for c in '/\\:') for p in parts):
                raise ValueError('Invalid compiled persistent-state scope')
            return user_local_appdata().joinpath(*parts)
        return Path(sys.executable).absolute().parent/'state'
    return Path(__file__).resolve().parents[2]


def projected_paths(root):
    """Conservative unchanged Win32 limit, including external transaction state."""
    return [root/'out'/kind/('0'*36)/'sessions'/('0'*36)/'blobs'/('0'*64)
            for kind in ('synthetic','external-transactions')]


def validate_portable_path(root):
    longest=max(projected_paths(root),key=lambda p:len(str(p)))
    if len(str(longest))>=260:
        label='Persistent per-user path too long' if persistent_profile() is not None else 'Package path too long'
        raise ValueError(label+': projected transaction path is '+str(len(str(longest)))+
                         ' characters (supported limit: 259). Move/re-extract the COMPLETE package to a short writable C: folder, '+
                         'for example C:\\VRKMI. Keep Backend adjacent to the EXE. '+
                         'If transaction state already exists, preserve it; do not delete it to bypass this check.')


def initialize_portable():
    if not getattr(sys,'frozen',False): return workspace()
    from .validator import no_links
    from .recovery import read_json, exclusive_bytes, canonical, file_id, SafetyError
    root=workspace()
    validate_portable_path(root)
    if persistent_profile() is not None:
        # Same inherited per-user permissions; no ACL/elevation changes.
        base=user_local_appdata();no_links(base)
        current=base
        for part in persistent_profile()[:-1]:
            current=current/part
            if not current.exists():current.mkdir()
            no_links(current)
        # Reject any extraction/temp-root placement even in a malformed compiled profile.
        import tempfile
        temp=Path(tempfile.gettempdir())
        if root==temp or temp in root.parents:raise SafetyError('Recovery state must not be temporary')
    no_links(root.parent)
    marker=root/'portable-state.json'
    if root.exists() or root.is_symlink():
        no_links(root)
        value=read_json(marker)
        if value != {'schema':1,'scope':'portable-synthetic-only','root_id':file_id(root)}:
            raise SafetyError('unrecognized or moved portable state root')
    else:
        root.mkdir()
        exclusive_bytes(marker,canonical({'schema':1,'scope':'portable-synthetic-only','root_id':file_id(root)}))
    (root/'out').mkdir(exist_ok=True);no_links(root/'out')
    return root
