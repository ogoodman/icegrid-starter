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
        del self.queue[:]
        self._d.clear()

    def __len__(self):
        return len(self._d)

    def __contains__(self, key):
        return key in self._d

    def __iter__(self):
        return iter(self._d)

    def keys(self):
        return self._d.keys()

    def iteritems(self):
        return self._d.iteritems()


