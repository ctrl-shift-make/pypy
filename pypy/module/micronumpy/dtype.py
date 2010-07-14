﻿from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi

class TypeDescr(Wrappable):
    def __init__(self, dtype, name):
        self.dtype = dtype
        self.name = name
        self.w_native_type = None

    def descr_eq(self, space, w_type):
        if space.eq_w(self.w_native_type, w_type):
            return space.w_True

        try:
            typestr = space.str_w(w_type)
            if self.dtype.typecode == typestr: return space.w_True
            elif self.name == typestr: return space.w_True
            else: return space.w_False
        except OperationError, e:
            if e.match(space, space.w_TypeError): pass
            else: raise

        return space.w_False
    descr_eq.unwrap_spec = ['self', ObjSpace, W_Root]

    def descr_itemsize(self, space):
        return space.wrap(self.dtype.itemsize())
    descr_itemsize.unwrap_spec = ['self', ObjSpace]

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)
    descr_repr.unwrap_spec = ['self', ObjSpace]

TypeDescr.typedef = TypeDef('dtype',
                            itemsize = GetSetProperty(TypeDescr.descr_itemsize),
                            __eq__ = interp2app(TypeDescr.descr_eq),
                            __repr__ = interp2app(TypeDescr.descr_repr),
                           )

storage_type = lltype.Ptr(lltype.Array(lltype.Char))                           
null_storage = lltype.nullptr(storage_type.TO)

class DescrBase(object): pass

_typeindex = {}
_descriptors = []
_w_descriptors = []
def descriptor(code, name, ll_type):
    arraytype = lltype.Array(ll_type)
    class DescrImpl(DescrBase):
        def __init__(self):
            self.typeid = 0
            self.typecode = code

        def wrap(self, space, value):
            return space.wrap(value)

        def w_getitem(self, space, data, index):
            return space.wrap(self.getitem(data, index))

        def w_setitem(self, space, data, index, w_value):
            value = self.unwrap(space, w_value)
            self.setitem(data, index, value)

        def itemsize(self):
            return rffi.sizeof(ll_type)

        def getitem(self, data, index):
            array = rffi.cast(lltype.Ptr(arraytype), data)
            return array[index]

        def setitem(self, data, index, value):
            array = rffi.cast(lltype.Ptr(arraytype), data)
            #array[index] = rffi.cast(ll_type, value)
            array[index] = value # XXX: let's see if this works

        def alloc(self, count):
            #return lltype.malloc(arraytype, count, flavor='raw')
            mem = lltype.malloc(arraytype, count, flavor='raw')
            return rffi.cast(storage_type, mem)

        def free(self, data):
            lltype.free(data, flavor='raw')

        def wrappable_dtype(self):
            assert _w_descriptors[self.typeid].dtype is self, "This better be true."
            return _w_descriptors[self.typeid]

    for type in [lltype.Signed, lltype.Float]:
        def get_type(self, data, index):
            value = self.getitem(data, index)
            return rffi.cast(type, value)
        get_type.__name__ = 'get_%s' % type
        setattr(DescrImpl, 'get_%s' % type, get_type)

        def set_type(self, data, index, value):
            value = rffi.cast(ll_type, value)
            self.setitem(data, index, value)
        set_type.__name__ = 'set_%s' % type
        setattr(DescrImpl, 'set_%s' % type, set_type)

    DescrImpl.__name__ = 'Descr_%s' % name # XXX
                                
    typeid = len(_descriptors)

    _typeindex[code] = typeid
    descriptor = DescrImpl()
    descriptor.typeid = typeid

    _descriptors.append(descriptor)

    w_descriptor = TypeDescr(descriptor, name)
    _w_descriptors.append(w_descriptor)

    return descriptor

_typestring = {}
# int, int32 is l
# i is ??

int_descr = descriptor('i', 'int32', lltype.Signed)
type(int_descr).unwrap = lambda self, space, value: space.int_w(value)
_int_index = _typeindex['i']
_typestring['int32'] = _int_index
w_int_descr = _w_descriptors[_int_index]

float_descr = descriptor('d', 'float64', lltype.Float)
type(float_descr).unwrap = lambda self, space, value: space.float_w(value)
_float_index = _typeindex['d']
_typestring['float64'] = _float_index
w_float_descr = _w_descriptors[_float_index]

_result_types = {(_int_index, _int_index): _int_index,
                 (_int_index, _float_index): _float_index,
                 (_float_index, _int_index): _float_index,
                 (_float_index, _float_index): _float_index,
                }

def result(a, b):
    assert isinstance(a, DescrBase)
    assert isinstance(b, DescrBase)
    a = a.typeid
    b = b.typeid
    c = _result_types[(a, b)]
    return _descriptors[c]

def w_result(w_a, w_b):
    assert isinstance(w_a, TypeDescr)
    assert isinstance(w_b, TypeDescr)
    return result(w_a.dtype, w_b.dtype).wrappable_dtype()

def from_typecode(s):
    index = _typeindex[s]
    return _descriptors[index]

def from_typestring(s):
    index = _typestring[s]
    return _descriptors[index]

def from_wrapped_type(space, w_type):
    if w_type is space.w_int:
        return int_descr
    else:
        return float_descr #XXX: only handles two types!

def get(space, w_dtype):
    try:
        s = space.str_w(w_dtype)

        try:
            return from_typecode(s)
        except KeyError, e:
            return from_typestring(s)

    except KeyError, e:
        raise OperationError(space.w_TypeError,
                             space.wrap("data type not understood")
                            )

    except OperationError, e:
        if e.match(space, space.w_TypeError): pass # XXX: ValueError?

    try:
        i = space.int_w(w_dtype)
        return _descriptors[i]
    except OperationError, e:
        if e.match(space, space.w_TypeError): pass 
        else: raise

    return from_wrapped_type(space, w_dtype)

# FIXME: watch for wrapped typedescrs!
def infer_from_iterable(space, w_xs):
    highest_type = None
    dtype = None
    w_i = space.iter(w_xs)
    try:
        while True:
            w_element = space.next(w_i)      
            try:
                dtype = infer_from_iterable(space, w_element)
            except OperationError, e:
                if e.match(space, space.w_TypeError): # not iterable?
                    w_type = space.type(w_element)
                    dtype = from_wrapped_type(space, w_type)
                else: raise

            if highest_type is not None:
                a = highest_type.typeid   
                b = dtype.typeid
                highest_typeid = _result_types[(a, b)]
                highest_type = _descriptors[highest_typeid]
            else:
                highest_type = dtype
    except OperationError, e:
        if e.match(space, space.w_StopIteration):
            return highest_type
    else: raise
