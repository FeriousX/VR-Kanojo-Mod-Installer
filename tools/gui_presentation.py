"""Compatibility import for callers of the former tools presentation module."""
import sys as _sys
from pathlib import Path as _Path

if not getattr(_sys, 'frozen', False):
    _source = str(_Path(__file__).resolve().parents[1] / 'src')
    if _source not in _sys.path:
        _sys.path.insert(0, _source)

from hf_payload.transport.presentation import Counter, DESKTOP, presentation
