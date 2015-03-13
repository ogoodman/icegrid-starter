"""Tests for an LRU Cache."""

import unittest
import sys
import cStringIO
from lru_cache import LRUCache, LRUBase

class LRUCacheTest(unittest.TestCase):
    def test(self):
        cache = LRUCache(3)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3
        # eviction order is [a,b,c]
        self.assertEqual(cache['a'], 1)

        # eviction order is now [b,c,a]
        cache['d'] = 4
        # eviction order is [c,a,d]
        self.assertFalse('b' in cache)

        del cache['d']
        # eviction order is [c,a]
        cache['e'] = 5
        # eviction order [c,a,e]
        self.assertTrue('c' in cache)
        cache['f'] = 6
        # eviction order [a,e,f]
        self.assertFalse('c' in cache)

    def testFailingGetitem(self):
        cache = LRUCache(3)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3
        self.assertRaises(KeyError, lambda: cache['d'])
        self.assertEqual(set(cache.keys()), set(cache.queue))

    def testOnExpel(self):
        cache = LRUCache(2)
        expelled = []

        def callback(key, value):
            expelled.append((key, value))

        cache.onExpel(callback)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(expelled, [('a', 1)])

        cache.clear()
        self.assertEqual(len(cache), 0)

        cache['d'] = 4
        self.assertEqual(len(expelled), 1)

    def testCallbackThrowing(self):
        old_stderr = sys.stderr
        sys.stderr = cStringIO.StringIO()

        cache = LRUCache(2)
        expelled = []

        def throw(key, value):
            raise Exception('bang')
        def callback(key, value):
            expelled.append((key, value))

        cache.onExpel(throw)
        cache.onExpel(callback)
        
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3 # expulsion of 'a' will cause throw to be called.

        self.assertEqual(set(cache.queue), set(cache))
        self.assertEqual(expelled, [('a', 1)])

        self.assertTrue(bool(sys.stderr.getvalue())) # traceback written.
        sys.stderr = old_stderr

    def test_coverage(self):
        b = LRUBase(1)
        expelled = []
        def callback(k, v):
            expelled.append((k, v))
        b.onExpel(callback)
        b._updateQueue('a')
        b._updateQueue('b')
        self.assertEqual(expelled, [('a', None)])

if __name__ == '__main__':
    unittest.main()

