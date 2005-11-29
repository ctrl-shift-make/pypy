from pypy.translator.translator import TranslationContext
from pypy.rpython.test import snippet
from pypy.rpython.test.test_llinterp import interpret


class TestSnippet(object):

    def _test(self, func, types):
        t = TranslationContext()
        t.buildannotator().build_types(func, types)
        t.buildrtyper().specialize()
        t.checkgraphs()    
 
    def test_not1(self):
        self._test(snippet.not1, [float])

    def test_not2(self):
        self._test(snippet.not2, [float])

    def test_float1(self):
        self._test(snippet.float1, [float])

    def test_float_cast1(self):
        self._test(snippet.float_cast1, [float])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname

def test_int_conversion():
    def fn(f):
        return int(f)

    res = interpret(fn, [1.0])
    assert res == 1
    assert type(res) is int 
    res = interpret(fn, [2.34])
    assert res == fn(2.34) 

def test_float2str():
    def fn(f):
        return str(f)

    res = interpret(fn, [1.5])
    assert float(''.join(res.chars)) == 1.5
