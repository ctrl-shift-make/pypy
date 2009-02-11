import py
from pypy.rlib.jit import JitDriver
from policy import StopAtXPolicy
from pypy.rpython.ootypesystem import ootype
from test.test_basic import LLJitMixin, OOJitMixin


class SendTests:

    def test_green_send(self):
        myjitdriver = JitDriver(greens = ['i'], reds = ['counter'])
        lst = ["123", "45"]
        def f(i):
            counter = 20
            c = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                s = lst[i]
                c = len(s)
                counter -= 1
            return c
        res = self.meta_interp(f, [1])
        assert res == 2
        self.check_loops({'jump': 1, 'merge_point': 1,
                          'int_sub': 1, 'int_gt' : 1,
                          'guard_true': 1})    # all folded away

    def test_red_builtin_send(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 'counter'])
        lst = [{1:1, 2:2, 3:3}, {4:4, 5:5}]
        def externfn(i):
            return lst[i]
        def f(i):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                dct = externfn(i)
                res = len(dct)
                counter -= 1
            return res
        res = self.meta_interp(f, [1], policy=StopAtXPolicy(externfn))
        assert res == 2
        if self.type_system == 'ootype':
            self.check_loops(call_ptr=1, builtin=1) # 'len' remains
        else:
            # 'len' becomes a getfield('num_items') for now in lltype,
            # which is itself encoded as a 'getfield__4'
            self.check_loops(call_ptr=1, getfield_gc__4=1)

    def test_send_to_single_target_method(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 'counter'])
        class Foo:
            def meth(self, y):
                return self.x + y
        def externfn(i):
            foo = Foo()
            foo.x = i * 42
            return foo
        def f(i):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                foo = externfn(i)
                res = foo.meth(i)
                counter -= 1
            return res
        res = self.meta_interp(f, [1], policy=StopAtXPolicy(externfn),
                               backendopt=True)
        assert res == 43
        self.check_loops({'call_ptr': 1, 'guard_exception': 1,
                          'getfield_gc__4': 1,
                          'int_add': 1, 'merge_point' : 1,
                          'jump': 1, 'int_gt' : 1, 'guard_true' : 1,
                          'int_sub' : 1})

    def test_red_send_to_green_receiver(self):
        myjitdriver = JitDriver(greens = ['i'], reds = ['counter', 'j'])
        class Foo(object):
            def meth(self, i):
                return 42 + i
        class Foobar(Foo):
            def meth(self, i):
                return 146 + i
        lst = [Foo(), Foo(), Foobar(), Foo(), Foobar(), Foo()]
        def f(i, j):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i, j=j)
                myjitdriver.jit_merge_point(counter=counter, i=i, j=j)
                foo = lst[i]
                res = foo.meth(j)
                counter -= 1
            return res
        res = self.meta_interp(f, [4, -1])
        assert res == 145
        self.check_loops(int_add = 1)

    def test_oosend_base(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W1(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W2(self.y + 100)
            def getvalue(self):
                return self.y
        def f(x, y):
            if x & 1:
                w = W1(x)
            else:
                w = W2(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 14])
        assert res == 17
        res = self.meta_interp(f, [4, 14])
        assert res == 1404
        self.check_loops(guard_class=0, new_with_vtable=0)

    def test_three_receivers(self):
        myjitdriver = JitDriver(greens = [], reds = ['y'])
        class Base:
            pass
        class W1(Base):
            def foo(self):
                return 1
        class W2(Base):
            def foo(self):
                return 2
        class W3(Base):
            def foo(self):
                return 3
        def externfn(y):
            if y % 4 == 0: return W1()
            elif y % 4 == 3: return W2()
            else: return W3()
        def f(y):
            while y > 0:
                myjitdriver.can_enter_jit(y=y)
                myjitdriver.jit_merge_point(y=y)                
                w = externfn(y)
                w.foo()
                y -= 1
            return 42
        for j in range(69, 75):
            res = self.meta_interp(f, [j], policy=StopAtXPolicy(externfn))
            assert res == 42
            self.check_loop_count(3)

    def test_oosend_guard_failure(self):
        py.test.skip("Unsupported yet")
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W1(self.y + 100)
            def getvalue(self):
                return self.y
        def f(x, y):
            if x & 1:
                w = W1(x)
            else:
                w = W2(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        res = self.meta_interp(f, [4, 28])
        assert res == f(4, 28)
        # The effect of the ClassGuard generated by the oosend to incr()
        # should be to unroll the loop, giving two copies of the body in
        # a single bigger loop with no failing guard except the final one.
        self.check_loop_count(1)
        self.check_loops(guard_class=0,
                                int_add=2, int_sub=2)
        self.check_jumps(14)

    def test_oosend_guard_failure_2(self):
        py.test.skip("Unsupported yet")
        # same as above, but using prebuilt objects 'w1' and 'w2'
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W1(self.y + 100)
            def getvalue(self):
                return self.y
        w1 = W1(10)
        w2 = W2(20)
        def f(x, y):
            if x & 1:
                w = w1
            else:
                w = w2
            while y > 0:
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        res = self.meta_interp(f, [4, 28])
        assert res == f(4, 28)
        self.check_loop_count(1)
        self.check_loops(guard_class=0,
                                int_add=2, int_sub=2)
        self.check_jumps(14)

    def test_oosend_different_initial_class(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W2(self.y * 2)
            def getvalue(self):
                return self.y
        def f(x, y):
            w = W1(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        # The effect of the ClassGuard generated by the oosend to incr()
        # should be to unroll the first iteration of the loop.  Indeed,
        # looking only at the loop, we deduce that the class of 'w' is 'W2'.
        # However, this doesn't match the initial value of 'w'.
        # XXX This not completely easy to check...
        self.check_loop_count(1)
        self.check_loops(int_add=0, int_mul=1, guard_class=0)

    def test_example(self):
        myjitdriver = JitDriver(greens = ['i'],
                                reds = ['res', 'a'])
        CO_INCREASE = 0
        CO_JUMP_BACK_3 = 1
        CO_DECREASE = 2
        
        code = [CO_INCREASE, CO_INCREASE, CO_INCREASE,
                CO_JUMP_BACK_3, CO_INCREASE, CO_DECREASE]
        
        def add(res, a):
            return res + a

        def sub(res, a):
            return res - a
        
        def main_interpreter_loop(a):
            i = 0
            res = 0
            c = len(code)
            while i < c:
                myjitdriver.jit_merge_point(res=res, i=i, a=a)
                elem = code[i]
                if elem == CO_INCREASE:
                    res = add(res, a)
                elif elem == CO_DECREASE:
                    res = sub(res, a)
                else:
                    if res > 100:
                        pass
                    else:
                        i = i - 3
                        myjitdriver.can_enter_jit(res=res, i=i, a=a)
                        continue
                i = i + 1
            return res

        res = self.meta_interp(main_interpreter_loop, [1])
        assert res == 102
        self.check_loop_count(1)
        self.check_loops({'merge_point' : 1, 'int_add' : 3, 'int_gt' : 1,
                          'guard_false' : 1, 'jump' : 1})

class TestOOtype(SendTests, OOJitMixin):
    pass

class TestLLtype(SendTests, LLJitMixin):
    pass
