from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.test import test_ll_random
from pypy.jit.backend.test import test_random
from pypy.jit.backend.test.test_ll_random import LLtypeOperationBuilder
from pypy.jit.backend.test.test_random import check_random_function, Random
from pypy.jit.metainterp.resoperation import rop

CPU = getcpuclass()

def test_stress():
    cpu = CPU(None, None)
    for i in range(1000):
        r = Random()
        check_random_function(cpu, LLtypeOperationBuilder, r, i, 1000)
