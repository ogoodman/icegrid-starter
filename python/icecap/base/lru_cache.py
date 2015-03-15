"""A dict which only remembers the n most-recently used entries."""

import threading
import traceback

class LRUBase(object):
    def __init__(self, n):
        self.n = n
        self.queue = []
        self.on_expel = []

    def onExpel(self, callback):
        if callback not in self.on_expel:
            self.on_expel.append(callback)

    def _updateQueue(self, key):
        if key in self.queue:
            self.queue.remove(key)
        else:
            excess = len(self.queue) - self.n + 1
            if excess > 0:
                for old_key in self.queue[0 : excess]:
                    value = self._popKey(old_key)
                    for callback in self.on_expel:
                        try:
                            callback(old_key, value)
                        except:
                            traceback.print_exc()
                del self.queue[0 : excess]
        self.queue.append(key)

    def _popKey(self, key):
        pass  # override to remove key and return the value

class LRUCache(LRUBase):
    """An LRUCache is a dictionary which remembers the *n* most recently accessed items.

    Usage::

        d = LRUCache(3)
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['a'] # -> returns 1, now 'b' is oldest
        d['d'] = 4

        d.keys() # -> [1, 3, 4]

    If you need to know when an item is expelled from the cache you
    can add a callback for it::

        d = LRUCache(1)
        def cleanup(k, v):
            print 'expelled', k, v
        d.onExpel(cleanup)
        d['x'] = True
        d['y'] = False # causes cleanup('x', True) to be called.

    .. note:: deliberate removals such as ``del d['x']`` or ``d.clear()`` will
        not trigger the callback, only cache evictions.

    The following dictionary operations are supported::

        d[key]         # indexing, updates the age
        del d[key]
        len(d)
        d[key] = value # key becomes newest, may cause an eviction
        key in d       # does not update the age
        iter(d)        # yields the keys, ages not updated
        d.iteritems()  # yields key-value pairs, ages not updated

    :param n: the number of items to remember
    """
    def __init__(self, n):
        LRUBase.__init__(self, n)
        self._d = {}

    def _popKey(self, key):
        return self._d.pop(key)

    def __getitem__(self, key):
        item = self._d[key]
        self._updateQueue(key)
        return item

    def __setitem__(self, key, value):
        self._d[key] = value
        self._updateQueue(key)

    def __delitem__(self, key):
        if key in self.queue:
            self.queue.remove(key)
        del self._d[key]

    def clear(self):
        """Remove all key-value pairs from the dictionary."""
        del self.queue[:]
        self._d.clear()

    def __len__(self):
        return len(self._d)

    def __contains__(self, key):
        return key in self._d

    def __iter__(self):
        return iter(self._d)

    def keys(self):
        """Returns a list of keys of the dictionary."""
        return self._d.keys()

    def iteritems(self):
        """Iterate over all key, value pairs in the dictionary."""
        return self._d.iteritems()


