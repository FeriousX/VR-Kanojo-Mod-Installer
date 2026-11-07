"""Build-process isolation only; never changes installer/runtime behavior."""
import os
from pathlib import Path

def isolated_build_environment(python, cache, inherited=None):
    source = dict(os.environ if inherited is None else inherited)
    executable = Path(python).resolve(strict=True)
    system_root = Path({k.upper():v for k,v in source.items()}['SYSTEMROOT']).resolve(strict=True)
    if not (system_root/'System32').is_dir():
        raise ValueError('Windows system directory is unavailable')
    # Drop host interpreter, dynamic-loader and PyInstaller configuration overrides.
    env = {k:v for k,v in source.items() if not k.upper().startswith(('PYTHON', 'PYINSTALLER', '_PYI_', 'LD_', 'DYLD_')) and k.upper() != 'PATH'}
    env['PATH'] = os.pathsep.join(map(str,(executable.parent,system_root/'System32',system_root)))
    env['PYINSTALLER_CONFIG_DIR'] = str(Path(cache).absolute())
    return env
