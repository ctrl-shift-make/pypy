
from pypy.rpython.extregistry import ExtRegistryEntry

class r_iter(object):
    def next(self):
        raise NotImplementedError("abstract base class")

class list_iter(object):
    def __init__(self, l):
        self.l = l
        self.pos = 0

    def next(self):
        if self.pos >= len(self.l):
            raise StopIteration
        res = self.l[self.pos]
        self.pos += 1
        return res

    def __iter__(self):
        """ NOT_RPYTHON, for untranslated version only
        """
        return self
        
