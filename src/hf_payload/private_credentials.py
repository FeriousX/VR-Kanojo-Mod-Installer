"""Windows CurrentUser DPAPI credentials for private test transactions.

Not protection from the same user/admin, state rollback, or key compromise.
"""
import ctypes,os
from ctypes import wintypes
from .recovery import SafetyError
class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def crypt(raw,decrypt=False):
    if os.name!='nt':raise SafetyError('private credentials require Windows DPAPI')
    buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    dll=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    if decrypt:
        call=dll.CryptUnprotectData
        call.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        result=call(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out))
    else:
        call=dll.CryptProtectData
        call.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        result=call(ctypes.byref(source),'HF private disposable transaction',None,None,None,1,ctypes.byref(out))
    call.restype=wintypes.BOOL
    if not result:raise SafetyError('DPAPI credential operation failed: '+str(ctypes.get_last_error()))
    try:return ctypes.string_at(out.data,out.size)
    finally:
        kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
        kernel.LocalFree(out.data)
