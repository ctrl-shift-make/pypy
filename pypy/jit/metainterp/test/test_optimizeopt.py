import py
from pypy.jit.metainterp.test.test_optimizefindnode import (LLtypeMixin,
                                                            OOtypeMixin,
                                                            BaseTest)
from pypy.jit.metainterp.optimizeopt import optimize
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.metainterp.test.oparser import parse

# ____________________________________________________________

def equaloplists(oplist1, oplist2):
    print '-'*20, 'Comparing lists', '-'*20
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = str(op1)
        txt2 = str(op2)
        while txt1 or txt2:
            print '%-39s| %s' % (txt1[:39], txt2[:39])
            txt1 = txt1[39:]
            txt2 = txt2[39:]
        assert op1.opnum == op2.opnum
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y
        assert op1.result == op2.result
        assert op1.descr == op2.descr
        if op1.suboperations:
            assert equaloplists(op1.suboperations, op2.suboperations)
    assert len(oplist1) == len(oplist2)
    print '-'*57
    return True

def test_equaloplists():
    ops = """
    [i0]
    i1 = int_add(i0, 1)
    guard_true(i1)
        i2 = int_add(i1, 1)
        fail(i2)
    jump(i1)
    """
    loop1 = parse(ops)
    loop2 = parse(ops)
    loop3 = parse(ops.replace("i2 = int_add", "i2 = int_sub"))
    assert equaloplists(loop1.operations, loop2.operations)
    py.test.raises(AssertionError,
                   "equaloplists(loop1.operations, loop3.operations)")

# ____________________________________________________________

class BaseTestOptimizeOpt(BaseTest):

    def assert_equal(self, optimized, expected):
        assert optimized.inputargs == expected.inputargs
        assert equaloplists(optimized.operations,
                            expected.operations)

    def optimize(self, ops, spectext, optops, boxkinds=None, **values):
        loop = self.parse(ops, boxkinds=boxkinds)
        loop.setvalues(**values)
        loop.specnodes = self.unpack_specnodes(spectext)
        optimize(loop)
        expected = self.parse(optops, boxkinds=boxkinds)
        self.assert_equal(loop, expected)

    def test_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0)
          fail(i0)
        jump(i)
        """
        self.optimize(ops, 'Not', ops, i0=0)

    def test_constant_propagate(self):
        ops = """
        []
        i0 = int_add(2, 3)
        i1 = int_is_true(i0)
        guard_true(i1)
          fail()
        i2 = bool_not(i1)
        guard_false(i2)
          fail()
        guard_value(i0, 5)
          fail()
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize(ops, '', expected, i0=5, i1=1, i2=0)

    def test_constfold_all(self):
        for op in range(rop.INT_ADD, rop.BOOL_NOT+1):
            try:
                op = opname[op]
            except KeyError:
                continue
            ops = """
            []
            i1 = %s(3, 2)
            jump()
            """ % op.lower()
            expected = """
            []
            jump()
            """
            self.optimize(ops, '', expected)

    # ----------

    def test_remove_guard_class(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        self.optimize(ops, 'Not', expected)

    def test_remove_consecutive_guard_value_constfold(self):
        ops = """
        [i0]
        guard_value(i0, 0)
          fail()
        i1 = int_add(i0, 1)
        guard_value(i1, 1)
          fail()
        i2 = int_add(i1, 2)
        jump(i2)
        """
        expected = """
        [i0]
        guard_value(i0, 0)
            fail()
        jump(3)
        """
        self.optimize(ops, 'Not', expected, i0=0, i1=1, i2=3)

    def test_ooisnull_oononnull_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        i0 = oononnull(p0)
        guard_true(i0)
          fail()
        i1 = ooisnull(p0)
        guard_false(i1)
          fail()
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        self.optimize(ops, 'Not', expected, i0=1, i1=0)

    def test_ooisnull_oononnull_2(self):
        py.test.skip("less important")
        ops = """
        [p0]
        i0 = oononnull(p0)         # p0 != NULL
        guard_true(i0)
          fail()
        i1 = ooisnull(p0)
        guard_false(i1)
          fail()
        jump(p0)
        """
        expected = """
        [p0]
        i0 = oononnull(p0)
        guard_true(i0)
          fail()
        jump(p0)
        """
        self.optimize(ops, 'Not', expected, i0=1, i1=0)

    def test_oois_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        i0 = ooisnot(p0, NULL)
        guard_true(i0)
          fail()
        i1 = oois(p0, NULL)
        guard_false(i1)
          fail()
        i2 = ooisnot(NULL, p0)
        guard_true(i0)
          fail()
        i3 = oois(NULL, p0)
        guard_false(i1)
          fail()
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable))
          fail()
        jump(p0)
        """
        self.optimize(ops, 'Not', expected, i0=1, i1=0, i2=1, i3=0)


class TestLLtype(BaseTestOptimizeOpt, LLtypeMixin):
    pass

class TestOOtype(BaseTestOptimizeOpt, OOtypeMixin):
    pass
