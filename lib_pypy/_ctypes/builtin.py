
import _rawffi, sys

class ConvMode:
    encoding = 'ascii'
    errors = 'strict'

_memmove_addr = _rawffi.get_libc().getaddressindll('memmove')
_memset_addr = _rawffi.get_libc().getaddressindll('memset')

def _string_at_addr(addr, lgt):
    # address here can be almost anything
    import ctypes
    cobj = ctypes.c_void_p.from_param(addr)
    arg = cobj._get_buffer_value()
    return _rawffi.charp2rawstring(arg, lgt)

def set_conversion_mode(encoding, errors):
    old_cm = ConvMode.encoding, ConvMode.errors
    ConvMode.errors = errors
    ConvMode.encoding = encoding
    return old_cm

def _wstring_at_addr(addr, lgt):
    import ctypes
    cobj = ctypes.c_void_p.from_param(addr)
    arg = cobj._get_buffer_value()
    return _rawffi.wcharp2rawunicode(arg, lgt)
