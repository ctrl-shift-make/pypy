from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.unicodedata import unicodedb_4_1_0 as unicodedb
from pypy.module.cpyext.api import (CANNOT_FAIL, Py_ssize_t,
                                    build_type_checkers, cpython_api,
                                    bootstrap_function, generic_cpy_call)
from pypy.module.cpyext.pyerrors import PyErr_BadArgument
from pypy.module.cpyext.pyobject import PyObject, from_ref, make_ref, Py_DecRef, make_typedescr
from pypy.module.cpyext.stringobject import PyString_Check
from pypy.module.sys.interp_encoding import setdefaultencoding
from pypy.objspace.std import unicodeobject, unicodetype

PyUnicodeObjectStruct = lltype.ForwardReference()
PyUnicodeObject = lltype.Ptr(PyUnicodeObjectStruct)
PyUnicodeObjectFields = (PyObjectFields +
    (("buffer", rffi.CWCHARP), ("size", Py_ssize_t)))
cpython_struct("PyUnicodeObject", PyUnicodeObjectFields, PyUnicodeObjectStruct)

@bootstrap_function
def init_unicodeobject(space):
    make_typedescr(space.w_unicode.instancetypedef,
                   basestruct=PyUnicodeObject.TO,
                   dealloc=unicode_dealloc)

# Buffer for the default encoding (used by PyUnicde_GetDefaultEncoding)
DEFAULT_ENCODING_SIZE = 100
default_encoding = lltype.malloc(rffi.CCHARP.TO, DEFAULT_ENCODING_SIZE,
                                 flavor='raw', zero=True)

PyUnicode_Check, PyUnicode_CheckExact = build_type_checkers("Unicode", "w_unicode")

Py_UNICODE = lltype.UniChar

@cpython_api([PyObject], lltype.Void, external=False)
def unicode_dealloc(space, obj):
    obj = rffi.cast(PyUnicodeObject, obj)
    pto = obj.c_ob_type
    if obj.c_buffer:
        lltype.free(obj.c_buffer, flavor="raw")
    obj_voidp = rffi.cast(rffi.VOIDP_real, obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)
    pto = rffi.cast(PyObject, pto)
    Py_DecRef(space, pto)

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALNUM(space, ch):
    """Return 1 or 0 depending on whether ch is an alphanumeric character."""
    return unicodedb.isalnum(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLINEBREAK(space, ch):
    """Return 1 or 0 depending on whether ch is a linebreak character."""
    return unicodedb.islinebreak(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISSPACE(space, ch):
    """Return 1 or 0 depending on whether ch is a whitespace character."""
    return unicodedb.isspace(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISALNUM(space, ch):
    """Return 1 or 0 depending on whether ch is an alphanumeric character."""
    return unicodedb.isalnum(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISDECIMAL(space, ch):
    """Return 1 or 0 depending on whether ch is a decimal character."""
    return unicodedb.isdecimal(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISLOWER(space, ch):
    """Return 1 or 0 depending on whether ch is a lowercase character."""
    return unicodedb.islower(ord(ch))

@cpython_api([Py_UNICODE], rffi.INT_real, error=CANNOT_FAIL)
def Py_UNICODE_ISUPPER(space, ch):
    """Return 1 or 0 depending on whether ch is an uppercase character."""
    return unicodedb.isupper(ord(ch))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOLOWER(space, ch):
    """Return the character ch converted to lower case."""
    return unichr(unicodedb.tolower(ord(ch)))

@cpython_api([Py_UNICODE], Py_UNICODE, error=CANNOT_FAIL)
def Py_UNICODE_TOUPPER(space, ch):
    """Return the character ch converted to upper case."""
    return unichr(unicodedb.toupper(ord(ch)))

@cpython_api([PyObject], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_DATA(space, ref):
    """Return a pointer to the internal buffer of the object. o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.cast(rffi.CCHARP, PyUnicode_AS_UNICODE(space, ref))

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_DATA_SIZE(space, w_obj):
    """Return the size of the object's internal buffer in bytes.  o has to be a
    PyUnicodeObject (not checked)."""
    return rffi.sizeof(lltype.UniChar) * PyUnicode_GET_SIZE(space, w_obj)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyUnicode_GET_SIZE(space, w_obj):
    """Return the size of the object.  o has to be a PyUnicodeObject (not
    checked).

    This function returned an int type. This might require changes
    in your code for properly supporting 64-bit systems."""
    assert isinstance(w_obj, unicodeobject.W_UnicodeObject)
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject], rffi.CWCHARP, error=CANNOT_FAIL)
def PyUnicode_AS_UNICODE(space, ref):
    """Return a pointer to the internal Py_UNICODE buffer of the object.  ref
    has to be a PyUnicodeObject (not checked)."""
    ref_unicode = rffi.cast(PyUnicodeObject, ref)
    if not ref_unicode.c_buffer:
        # Copy unicode buffer
        w_unicode = from_ref(space, ref)
        u = space.unicode_w(w_unicode)
        ref_unicode.c_buffer = rffi.unicode2wcharp(u)
    return ref_unicode.c_buffer

@cpython_api([PyObject], rffi.CWCHARP, error=lltype.nullptr(rffi.CWCHARP.TO))
def PyUnicode_AsUnicode(space, ref):
    """Return a read-only pointer to the Unicode object's internal Py_UNICODE
    buffer, NULL if unicode is not a Unicode object."""
    if not PyUnicode_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected unicode object"))
    return PyUnicode_AS_UNICODE(space, ref)

@cpython_api([], rffi.CCHARP, error=CANNOT_FAIL)
def PyUnicode_GetDefaultEncoding(space):
    """Returns the currently active default encoding."""
    if default_encoding[0] == '\x00':
        encoding = unicodetype.getdefaultencoding(space)
        i = 0
        while i < len(encoding) and i < DEFAULT_ENCODING_SIZE:
            default_encoding[i] = encoding[i]
            i += 1
    return default_encoding

@cpython_api([rffi.CCHARP], rffi.INT_real, error=-1)
def PyUnicode_SetDefaultEncoding(space, encoding):
    """Sets the currently active default encoding. Returns 0 on
    success, -1 in case of an error."""
    w_encoding = space.wrap(rffi.charp2str(encoding))
    setdefaultencoding(space, w_encoding)
    default_encoding[0] = '\x00'
    return 0

@cpython_api([PyObject, rffi.CCHARP, rffi.CCHARP], PyObject)
def PyUnicode_AsEncodedString(space, w_unicode, encoding, errors):
    """Encode a Unicode object and return the result as Python string object.
    encoding and errors have the same meaning as the parameters of the same name
    in the Unicode encode() method. The codec to be used is looked up using
    the Python codec registry. Return NULL if an exception was raised by the
    codec."""
    if not PyUnicode_Check(space, w_unicode):
        PyErr_BadArgument(space)

    w_encoding = w_errors = None
    if encoding:
        w_encoding = rffi.charp2str(encoding)
    if errors:
        w_errors = rffi.charp2str(encoding)
    return unicodetype.encode_object(space, w_unicode, w_encoding, w_errors)

@cpython_api([rffi.CWCHARP, Py_ssize_t], PyObject)
def PyUnicode_FromUnicode(space, wchar_p, length):
    """Create a Unicode Object from the Py_UNICODE buffer u of the given size. u
    may be NULL which causes the contents to be undefined. It is the user's
    responsibility to fill in the needed data.  The buffer is copied into the new
    object. If the buffer is not NULL, the return value might be a shared object.
    Therefore, modification of the resulting Unicode object is only allowed when u
    is NULL."""
    if not wchar_p:
        raise NotImplementedError
    s = rffi.wcharpsize2unicode(wchar_p, length)
    ptr = make_ref(space, space.wrap(s))
    return ptr

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def _PyUnicode_AsDefaultEncodedString(space, w_unicode, errors):
    return PyUnicode_AsEncodedString(space, w_unicode, lltype.nullptr(rffi.CCHARP.TO), errors)
