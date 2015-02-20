import sys

from rpython.rlib import rposix

from pypy.interpreter.gateway import unwrap_spec

WIN32 = sys.platform == 'win32'
if WIN32:
    from rpython.rlib import rwin32


_errno_before = rposix._errno_before
_errno_after  = rposix._errno_after

def get_errno(space):
    return space.wrap(rposix.get_saved_errno())

@unwrap_spec(errno=int)
def set_errno(space, errno):
    rposix.set_saved_errno(errno)

# ____________________________________________________________

@unwrap_spec(code=int)
def getwinerror(space, code=-1):
    from rpython.rlib.rwin32 import GetLastError_saved, FormatError
    if code == -1:
        code = GetLastError_saved()
    message = FormatError(code)
    return space.newtuple([space.wrap(code), space.wrap(message)])
