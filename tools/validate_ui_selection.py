"""Compatibility entry point for the relocated stdin/stdout selection adapter."""
import sys as _sys
from pathlib import Path as _Path

if not getattr(_sys, 'frozen', False):
    _source = str(_Path(__file__).resolve().parents[1] / 'src')
    if _source not in _sys.path:
        _sys.path.insert(0, _source)

import hf_payload.transport.selection_cli as _implementation

if __name__ == '__main__':
    _sys.exit(_implementation.main())
else:
    # One module object preserves original exported names and patched globals.
    _sys.modules[__name__] = _implementation
