import py
from pypy.rpython.lltypesystem import lltype, lloperation, rclass, llmemory
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.rlib.jit import JitDriver, hint
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rpython.lltypesystem.rvirtualizable2 import VABLERTIPTR
from pypy.rpython.lltypesystem.rvirtualizable2 import VirtualizableAccessor
from pypy.jit.metainterp.warmspot import get_stats
from pypy.jit.metainterp import history, heaptracker
from pypy.jit.metainterp.test.test_optimize import NODE

promote_virtualizable = lloperation.llop.promote_virtualizable
debug_print = lloperation.llop.debug_print

# ____________________________________________________________

class ExplicitVirtualizableTests:

    XY = lltype.GcStruct(
        'XY',
        ('parent', rclass.OBJECT),
        ('vable_base', llmemory.Address),
        ('vable_rti', VABLERTIPTR),
        ('inst_x', lltype.Signed),
        ('inst_node', lltype.Ptr(NODE)),
        hints = {'virtualizable2_accessor': VirtualizableAccessor()})
    XY._hints['virtualizable2_accessor'].initialize(
        XY, ['inst_x', 'inst_node'])

    xy_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    heaptracker.set_testing_vtable_for_gcstruct(XY, xy_vtable, 'XY')

    def _freeze_(self):
        return True

    def setup(self):
        xy = lltype.malloc(self.XY)
        xy.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
        xy.parent.typeptr = self.xy_vtable
        return xy

    def test_preexisting_access(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def f(n):
            xy = self.setup()
            xy.inst_x = 10
            while n > 0:
                myjitdriver.can_enter_jit(xy=xy, n=n)
                myjitdriver.jit_merge_point(xy=xy, n=n)
                promote_virtualizable(lltype.Void, xy, 'inst_x')
                x = xy.inst_x
                xy.inst_x = x + 1
                n -= 1
            return xy.inst_x
        res = self.meta_interp(f, [20])
        assert res == 30
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_preexisting_access_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def f(n):
            xy = self.setup()
            xy.inst_x = 100
            while n > -8:
                myjitdriver.can_enter_jit(xy=xy, n=n)
                myjitdriver.jit_merge_point(xy=xy, n=n)
                if n > 0:
                    promote_virtualizable(lltype.Void, xy, 'inst_x')
                    x = xy.inst_x
                    xy.inst_x = x + 1
                else:
                    promote_virtualizable(lltype.Void, xy, 'inst_x')
                    x = xy.inst_x
                    xy.inst_x = x + 10
                n -= 1
            return xy.inst_x
        assert f(5) == 185
        res = self.meta_interp(f, [5])
        assert res == 185
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_two_paths_access(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def f(n):
            xy = self.setup()
            xy.inst_x = 100
            while n > 0:
                myjitdriver.can_enter_jit(xy=xy, n=n)
                myjitdriver.jit_merge_point(xy=xy, n=n)
                promote_virtualizable(lltype.Void, xy, 'inst_x')
                x = xy.inst_x
                if n <= 10:
                    x += 1000
                xy.inst_x = x + 1
                n -= 1
            return xy.inst_x
        res = self.meta_interp(f, [18])
        assert res == 10118
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_synchronize_in_return(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def g(xy, n):
            while n > 0:
                myjitdriver.can_enter_jit(xy=xy, n=n)
                myjitdriver.jit_merge_point(xy=xy, n=n)
                promote_virtualizable(lltype.Void, xy, 'inst_x')
                xy.inst_x += 1
                n -= 1
        def f(n):
            xy = self.setup()
            xy.inst_x = 10000
            m = 10
            while m > 0:
                g(xy, n)
                m -= 1
            return xy.inst_x
        res = self.meta_interp(f, [18])
        assert res == 10180
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_virtualizable_and_greens(self):
        myjitdriver = JitDriver(greens = ['m'], reds = ['n', 'xy'],
                                virtualizables = ['xy'])
        def g(n):
            xy = self.setup()
            xy.inst_x = 10
            m = 0
            while n > 0:
                myjitdriver.can_enter_jit(xy=xy, n=n, m=m)
                myjitdriver.jit_merge_point(xy=xy, n=n, m=m)
                promote_virtualizable(lltype.Void, xy, 'inst_x')
                x = xy.inst_x
                xy.inst_x = x + 1
                m = (m+1) & 3     # the loop gets unrolled 4 times
                n -= 1
            return xy.inst_x
        def f(n):
            res = 0
            k = 4
            while k > 0:
                res += g(n)
                k -= 1
            return res
        res = self.meta_interp(f, [40])
        assert res == 50 * 4
        self.check_loops(getfield_gc=0, setfield_gc=0)

    # ------------------------------

    XY2 = lltype.GcStruct(
        'XY2',
        ('parent', rclass.OBJECT),
        ('vable_base', llmemory.Address),
        ('vable_rti', VABLERTIPTR),
        ('inst_x', lltype.Signed),
        ('inst_l1', lltype.Ptr(lltype.GcArray(lltype.Signed))),
        ('inst_l2', lltype.Ptr(lltype.GcArray(lltype.Signed))),
        hints = {'virtualizable2_accessor': VirtualizableAccessor()})
    XY2._hints['virtualizable2_accessor'].initialize(
        XY2, ['inst_x', 'inst_l1[*]', 'inst_l2[*]'])

    xy2_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    heaptracker.set_testing_vtable_for_gcstruct(XY2, xy2_vtable, 'XY2')

    def setup2(self):
        xy2 = lltype.malloc(self.XY2)
        xy2.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
        xy2.parent.typeptr = self.xy2_vtable
        return xy2

    def test_access_list_fields(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy2'],
                                virtualizables = ['xy2'])
        ARRAY = lltype.GcArray(lltype.Signed)
        def f(n):
            xy2 = self.setup2()
            xy2.inst_x = 100
            xy2.inst_l1 = lltype.malloc(ARRAY, 3)
            xy2.inst_l1[0] = -9999999
            xy2.inst_l1[1] = -9999999
            xy2.inst_l1[2] = 3001
            xy2.inst_l2 = lltype.malloc(ARRAY, 2)
            xy2.inst_l2[0] = 80
            xy2.inst_l2[1] = -9999999
            while n > 0:
                myjitdriver.can_enter_jit(xy2=xy2, n=n)
                myjitdriver.jit_merge_point(xy2=xy2, n=n)
                xy2.inst_l1[2] += xy2.inst_l2[0]
                n -= 1
            return xy2.inst_l1[2]
        res = self.meta_interp(f, [16])
        assert res == 3001 + 16 * 80
        self.check_loops(getfield_gc=0, setfield_gc=0,
                         getarrayitem_gc=0, setarrayitem_gc=0)

    def test_synchronize_arrays_in_return(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy2'],
                                virtualizables = ['xy2'])
        ARRAY = lltype.GcArray(lltype.Signed)
        def g(xy2, n):
            while n > 0:
                myjitdriver.can_enter_jit(xy2=xy2, n=n)
                myjitdriver.jit_merge_point(xy2=xy2, n=n)
                xy2.inst_l2[0] += xy2.inst_x
                n -= 1
        def f(n):
            xy2 = self.setup2()
            xy2.inst_x = 2
            xy2.inst_l1 = lltype.malloc(ARRAY, 2)
            xy2.inst_l1[0] = 1941309
            xy2.inst_l1[1] = 2941309
            xy2.inst_l2 = lltype.malloc(ARRAY, 1)
            xy2.inst_l2[0] = 10000
            m = 10
            while m > 0:
                g(xy2, n)
                m -= 1
            return xy2.inst_l2[0]
        assert f(18) == 10360
        res = self.meta_interp(f, [18])
        assert res == 10360
        self.check_loops(getfield_gc=0, setfield_gc=0,
                         getarrayitem_gc=0)

    def test_array_length(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy2'],
                                virtualizables = ['xy2'])
        ARRAY = lltype.GcArray(lltype.Signed)
        def g(xy2, n):
            while n > 0:
                myjitdriver.can_enter_jit(xy2=xy2, n=n)
                myjitdriver.jit_merge_point(xy2=xy2, n=n)
                xy2.inst_l1[1] += len(xy2.inst_l2)
                n -= 1
        def f(n):
            xy2 = self.setup2()
            xy2.inst_x = 2
            xy2.inst_l1 = lltype.malloc(ARRAY, 2)
            xy2.inst_l1[0] = 1941309
            xy2.inst_l1[1] = 2941309
            xy2.inst_l2 = lltype.malloc(ARRAY, 1)
            xy2.inst_l2[0] = 10000
            g(xy2, n)
            return xy2.inst_l1[1]
        res = self.meta_interp(f, [18])
        assert res == 2941309 + 18
        self.check_loops(getfield_gc=0, setfield_gc=0,
                         getarrayitem_gc=0, arraylen_gc=0)

    def test_residual_function(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy2'],
                                virtualizables = ['xy2'])
        ARRAY = lltype.GcArray(lltype.Signed)
        def h(xy2):
            # so far, this function is marked for residual calls because
            # it does something with a virtualizable's array that is not
            # just accessing an item
            return xy2.inst_l2
        def g(xy2, n):
            while n > 0:
                myjitdriver.can_enter_jit(xy2=xy2, n=n)
                myjitdriver.jit_merge_point(xy2=xy2, n=n)
                xy2.inst_l1[1] = xy2.inst_l1[1] + len(h(xy2))
                n -= 1
        def f(n):
            xy2 = self.setup2()
            xy2.inst_x = 2
            xy2.inst_l1 = lltype.malloc(ARRAY, 2)
            xy2.inst_l1[0] = 1941309
            xy2.inst_l1[1] = 2941309
            xy2.inst_l2 = lltype.malloc(ARRAY, 1)
            xy2.inst_l2[0] = 10000
            g(xy2, n)
            return xy2.inst_l1[1]
        res = self.meta_interp(f, [18])
        assert res == 2941309 + 18
        self.check_loops(getfield_gc=0, setfield_gc=0,
                         getarrayitem_gc=0, arraylen_gc=1, call=1)

    # ------------------------------

    XY2SUB = lltype.GcStruct(
        'XY2SUB',
        ('parent', XY2))

    xy2sub_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    heaptracker.set_testing_vtable_for_gcstruct(XY2SUB, xy2sub_vtable,
                                                'XY2SUB')

    def setup2sub(self):
        xy2 = lltype.malloc(self.XY2SUB)
        xy2.parent.vable_rti = lltype.nullptr(VABLERTIPTR.TO)
        xy2.parent.parent.typeptr = self.xy2_vtable
        return xy2

    def test_subclass(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'xy2'],
                                virtualizables = ['xy2'])
        ARRAY = lltype.GcArray(lltype.Signed)
        def g(xy2, n):
            while n > 0:
                myjitdriver.can_enter_jit(xy2=xy2, n=n)
                myjitdriver.jit_merge_point(xy2=xy2, n=n)
                xy2.parent.inst_l2[0] += xy2.parent.inst_x
                n -= 1
        def f(n):
            xy2 = self.setup2sub()
            xy2.parent.inst_x = 2
            xy2.parent.inst_l1 = lltype.malloc(ARRAY, 2)
            xy2.parent.inst_l1[0] = 1941309
            xy2.parent.inst_l1[1] = 2941309
            xy2.parent.inst_l2 = lltype.malloc(ARRAY, 1)
            xy2.parent.inst_l2[0] = 10000
            m = 10
            while m > 0:
                g(xy2, n)
                m -= 1
            return xy2.parent.inst_l2[0]
        assert f(18) == 10360
        res = self.meta_interp(f, [18])
        assert res == 10360
        self.check_loops(getfield_gc=0, setfield_gc=0,
                         getarrayitem_gc=0)

    # ------------------------------


class ImplicitVirtualizableTests:

    def test_simple_implicit(self):
        myjitdriver = JitDriver(greens = [], reds = ['frame'],
                                virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = ['x', 'y']

            def __init__(self, x, y):
                self.x = x
                self.y = y

        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def f(n):
            frame = Frame(n, 0)
            somewhere_else.top_frame = frame        # escapes
            while frame.x > 0:
                myjitdriver.can_enter_jit(frame=frame)
                myjitdriver.jit_merge_point(frame=frame)
                frame.y += frame.x
                frame.x -= 1
            return somewhere_else.top_frame.y

        res = self.meta_interp(f, [10])
        assert res == 55
        self.check_loops(getfield_gc=0, setfield_gc=0)


    def test_virtualizable_with_array(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'frame', 'x'],
                                virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = ['l[*]', 's']

            def __init__(self, l, s):
                self.l = l
                self.s = s
        
        def f(n, a):
            frame = Frame([a,a+1,a+2,a+3], 0)
            x = 0
            while n > 0:
                myjitdriver.can_enter_jit(frame=frame, n=n, x=x)
                myjitdriver.jit_merge_point(frame=frame, n=n, x=x)
                frame.s = hint(frame.s, promote=True)
                n -= 1
                x += frame.l[frame.s]
                frame.s += 1
                x += frame.l[frame.s]
                x += len(frame.l)
                frame.s -= 1
            return x

        res = self.meta_interp(f, [10, 1], listops=True)
        assert res == f(10, 1)
        self.check_loops(getarrayitem_gc=0)


    def test_subclass_of_virtualizable(self):
        myjitdriver = JitDriver(greens = [], reds = ['frame'],
                                virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = ['x', 'y']

            def __init__(self, x, y):
                self.x = x
                self.y = y

        class SubFrame(Frame):
            pass

        def f(n):
            Frame(0, 0)    # hack: make sure x and y are attached to Frame
            frame = SubFrame(n, 0)
            while frame.x > 0:
                myjitdriver.can_enter_jit(frame=frame)
                myjitdriver.jit_merge_point(frame=frame)
                frame.y += frame.x
                frame.x -= 1
            return frame.y

        res = self.meta_interp(f, [10])
        assert res == 55
        self.check_loops(getfield_gc=0, setfield_gc=0)


    def test_virtualizable_with_list(self):
        py.test.skip("redo or fix")
        myjitdriver = JitDriver(greens = [], reds = ['n', 'frame', 'x'],
                                virtualizables = ['frame'])


        class Frame(object):
            _virtualizable2_ = True

            def __init__(self, l, s):
                self.l = l
                self.s = s
        
        def f(n, a):
            frame = Frame([a,a+1,a+2,a+3], 0)
            x = 0
            while n > 0:
                myjitdriver.can_enter_jit(frame=frame, n=n, x=x)
                myjitdriver.jit_merge_point(frame=frame, n=n, x=x)
                frame.s = hint(frame.s, promote=True)
                n -= 1
                x += frame.l[frame.s]
                frame.s += 1
                x += frame.l[frame.s]
                frame.l[frame.s] += 1
                frame.s -= 1
            return x

        res = self.meta_interp(f, [10, 1], listops=True)
        assert res == f(10, 1)
        self.check_loops(setarrayitem_gc=1)

    def test_virtual_on_virtualizable(self):
        py.test.skip("redo or fix")
        myjitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                                virtualizables = ['frame'])

        class Stuff(object):
            def __init__(self, x):
                self.x = x

        class Stuff2(Stuff):
            pass

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['stuff']
            
            def __init__(self, x):
                self.stuff = Stuff(x)

        def f(n):
            frame = Frame(n/10)
            while n > 0:
                myjitdriver.can_enter_jit(frame=frame, n=n)
                myjitdriver.jit_merge_point(frame=frame, n=n)
                if isinstance(frame.stuff, Stuff2):
                    return 2
                n -= frame.stuff.x
            return n

        res = self.meta_interp(f, [30])
        assert res == f(30)
        self.check_loops(getfield_gc=0)


    def test_no_virtual_on_virtualizable(self):
        py.test.skip("redo or fix")
        myjitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                                virtualizables = ['frame'])

        class Stuff(object):
            def __init__(self, x):
                self.x = x

        class Stuff2(Stuff):
            pass

        class Frame(object):
            _virtualizable2_ = True
            
            def __init__(self, x):
                self.stuff = Stuff(x)

        def f(n):
            frame = Frame(n/10)
            while n > 0:
                myjitdriver.can_enter_jit(frame=frame, n=n)
                myjitdriver.jit_merge_point(frame=frame, n=n)
                if isinstance(frame.stuff, Stuff2):
                    return 2
                n -= frame.stuff.x
            return n

        res = self.meta_interp(f, [30])
        assert res == f(30)
        self.check_loops(getfield_gc=1)

    def test_unequal_list_lengths_cannot_be_virtual(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True
            def __init__(self):
                self.l = []

        def f(n):
            frame = Frame()
            while n > 0:
                jitdriver.can_enter_jit(n=n, frame=frame)
                jitdriver.jit_merge_point(n=n, frame=frame)
                frame.l.append(n)
                n -= 1
            sum = 0
            for i in range(len(frame.l)):
                sum += frame.l[i]
            return sum

        res = self.meta_interp(f, [20])
        assert res == f(20)

    def test_virtualizable_hierarchy(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                              virtualizables = ['frame'])

        class BaseFrame(object):
            _virtualizable2_ = True

            def __init__(self, x):
                self.x = x

        class Frame(BaseFrame):
            pass

        class Stuff(object):
            def __init__(self, x):
                self.x = x

        def f(n):
            frame = Frame(Stuff(3))

            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n)
                jitdriver.jit_merge_point(n=n, frame=frame)
                frame.x = Stuff(frame.x.x + 1)
                n -= 1
            return frame.x.x

        res = self.meta_interp(f, [20])
        assert res == f(20)
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_non_virtual_on_always_virtual(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['node']

            def __init__(self, node):
                self.node = node

        class Node(object):
            def __init__(self, node):
                self.node = node

        class SubNode(object):
            def __init__(self, x):
                self.x = x

        def g(node):
            pass

        def f(n):
            frame = Frame(Node(SubNode(1)))
            
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n)
                jitdriver.jit_merge_point(frame=frame, n=n)
                node = frame.node
                subnode = node.node
                g(subnode)
                frame.node.node = SubNode(subnode.x + 1)
                n -= 1
            return n

        res = self.meta_interp(f, [10], policy=StopAtXPolicy(g))
        self.check_loops(getfield_gc=1)
        assert res == 0

    def test_external_pass(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n', 'z'],
                              virtualizables = ['frame'])

        class BaseFrame(object):
            _virtualizable2_ = True

            def __init__(self, x):
                self.x = x

        class Frame(BaseFrame):
            pass

        def g(x):
            return x[1] == 1

        def f(n):
            frame = Frame([1,2,3])
            z = 0
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n, z=z)
                jitdriver.jit_merge_point(frame=frame, n=n, z=z)
                z += g(frame.x)
                n -= 1
            return z

        res = self.meta_interp(f, [10], policy=StopAtXPolicy(g))
        assert res == f(10)

    def test_always_virtual_with_origfields(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['l']

            def __init__(self, l):
                self.l = l

        def f(n):
            frame = Frame([1,2,3])
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n)
                jitdriver.jit_merge_point(frame=frame, n=n)
                n -= frame.l[0]
            return frame.l[1]

        res = self.meta_interp(f, [10], listops=True)
        assert res == 2

    def test_pass_always_virtual_to_bridge(self):
        py.test.skip("redo or fix")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['l']

            def __init__(self, l):
                self.l = l

        def f(n):
            frame = Frame([1,1,3])
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n)
                jitdriver.jit_merge_point(frame=frame, n=n)
                if n % 2:
                    n -= frame.l[0]
                else:
                    n -= frame.l[1]
            return frame.l[2]

        res = self.meta_interp(f, [30], listops=True)
        self.check_loops(setarrayitem_gc=0)
        self.check_loop_count(2) # -- this is hard to predict right now:
        #  what occurs is that one path through the loop is compiled,
        #  then exits; then later when we compile again we see the other
        #  path of the loop by chance, then exits; then finally we see
        #  again one loop or the other, and this time we make a bridge.
        #  So dependening on details we may or may not compile the other
        #  path as an independent loop.
        assert res == 3
        if self.basic:
            for loop in get_stats().loops:
                for op in loop._all_operations():
                    if op.getopname() == "int_sub":
                        assert isinstance(op.args[0], history.BoxInt)
                        assert isinstance(op.args[1], history.BoxInt)

    def test_virtual_obj_on_always_virtual(self):
        py.test.skip("redo or fix")
        py.test.skip("Bugs!")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n', 's'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['l']

            def __init__(self, l):
                self.l = l

        class Stuff(object):
            def __init__(self, elem):
                self.elem = elem

        def f(n):
            frame = Frame([Stuff(3), Stuff(4)])
            s = 0
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n, s=s)
                jitdriver.jit_merge_point(frame=frame, n=n, s=s)
                if n % 2:
                    s += frame.l[0].elem
                    frame.l[0] = Stuff(n)
                else:
                    s += frame.l[1].elem
                    frame.l[1] = Stuff(n)
                n -= 1
            return (frame.l[0].elem << 16) + frame.l[1].elem

        res = self.meta_interp(f, [30], listops=True)
        self.check_loops(getfield_gc=0)
        assert res == f(30)


    def test_virtual_obj_on_always_virtual_more_bridges(self):
        py.test.skip("redo or fix")
        py.test.skip("Bugs!")
        jitdriver = JitDriver(greens = [], reds = ['frame', 'n', 's'],
                              virtualizables = ['frame'])

        class Frame(object):
            _virtualizable2_ = True

            _always_virtual_ = ['l']

            def __init__(self, l):
                self.l = l

        class Stuff(object):
            def __init__(self, elem):
                self.elem = elem

        def f(n):
            frame = Frame([Stuff(3), Stuff(4)])
            s = 0
            while n > 0:
                jitdriver.can_enter_jit(frame=frame, n=n, s=s)
                jitdriver.jit_merge_point(frame=frame, n=n, s=s)
                if n % 2:
                    s += frame.l[0].elem
                    frame.l[0] = Stuff(n)
                elif n % 3:
                    s += 1
                else:
                    s += frame.l[1].elem
                    frame.l[1] = Stuff(n)
                n -= 1
            return (frame.l[0].elem << 16) + frame.l[1].elem

        res = self.meta_interp(f, [60], listops=True)
        self.check_loops(getfield_gc=0)
        assert res == f(60)

    def test_external_read(self):
        py.test.skip("redo or fix")
        py.test.skip("Fails")
        jitdriver = JitDriver(greens = [], reds = ['frame'],
                              virtualizables = ['frame'])
        
        class Frame(object):
            _virtualizable2_ = True
        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def g():
            result = somewhere_else.top_frame.y     # external read
            debug_print(lltype.Void, '-+-+-+-+- external read:', result)
            return result

        def f(n):
            frame = Frame()
            frame.x = n
            frame.y = 10
            somewhere_else.top_frame = frame
            while frame.x > 0:
                jitdriver.can_enter_jit(frame=frame)
                jitdriver.jit_merge_point(frame=frame)
                frame.x -= g()
                frame.y += 1
            return frame.x

        res = self.meta_interp(f, [123], policy=StopAtXPolicy(g))
        assert res == f(123)
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_external_write(self):
        py.test.skip("redo or fix")
        py.test.skip("Fails")
        class Frame(object):
            _virtualizable2_ = True
        class SomewhereElse:
            pass
        somewhere_else = SomewhereElse()

        def g():
            result = somewhere_else.top_frame.y + 1
            debug_print(lltype.Void, '-+-+-+-+- external write:', result)
            somewhere_else.top_frame.y = result      # external read/write

        def f(n):
            frame = Frame()
            frame.x = n
            frame.y = 10
            somewhere_else.top_frame = frame
            while frame.x > 0:
                g()
                frame.x -= frame.y
            return frame.y

        res = self.meta_interp(f, [240], exceptions=False,
                               policy=StopAtXPolicy(g))
        assert res == f(240)
        self.check_loops(getfield_gc=0, setfield_gc=0)

    def test_list_implicit(self):
        py.test.skip("redo or fix")
        py.test.skip("in-progress")
        class Frame(object):
            _virtualizable2_ = True

        def f(n):
            frame = Frame()
            while n > 0:
                frame.lst = []
                frame.lst.append(n - 10)
                n = frame.lst[-1]
            return n + len(frame.lst)

        res = self.meta_interp(f, [53], exceptions=False)
        assert res == -6
        self.check_loops(getfield_gc=0, setfield_gc=0, call=0)

    def test_single_list_implicit(self):
        py.test.skip("redo or fix")
        py.test.skip("in-progress")
        class Frame(object):
            _virtualizable2_ = True

        def f(n):
            frame = Frame()
            frame.lst = [100, n]
            while n > 0:
                n = frame.lst.pop()
                frame.lst.append(n - 10)
            return frame.lst.pop()

        res = self.meta_interp(f, [53], exceptions=False)
        assert res == -17
        self.check_loops(getfield_gc=0, setfield_gc=0, call=0)


class TestOOtype(#ExplicitVirtualizableTests,
                 ImplicitVirtualizableTests,
                 OOJitMixin):
    pass

class TestLLtype(ExplicitVirtualizableTests,
                 ImplicitVirtualizableTests,
                 LLJitMixin):
    pass
