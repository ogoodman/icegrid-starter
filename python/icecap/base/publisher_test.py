"""Tests for Publisher."""

import unittest
import weakref
from publisher import SubscriberList, Publisher
from icecap.base.util import grabOutput

class A(object):
    # For testing of subscribing with bound methods.
    def __init__(self, target):
        self._target = target
        self._target.a_calls = []
    def foo(self, message, arg=None):
        self._target.a_calls.append((message, arg))

class SelfSub(Publisher):
    def __init__(self):
        Publisher.__init__(self)
        self.subscribe('foo', self._on_foo)
        self.foo_info = None
    def _on_foo(self, info):
        self.foo_info = info

class PublisherTest(unittest.TestCase):
    def testSubscriberList(self):
        sl = SubscriberList()
        self.assertEqual(len(list(sl.iteritems())), 0)

        a = A(self)

        self.b_calls = []
        def b(message, arg):
            self.b_calls.append((message, arg))

        sl.add(a.foo, 1)
        sl.add(b, 2)

        self.assertEqual(len(list(sl.iteritems())), 2)

        sl.notify('msg')
        self.assertEqual(self.a_calls, [('msg', 1)])
        self.assertEqual(self.b_calls, [('msg', 2)])

        del a # a should be gc'd
        del b # b should not be gc'd

        self.assertEqual(len(list(sl.iteritems())), 1)

        sl.notify(36)
        self.assertEqual(self.a_calls, [('msg', 1)])
        self.assertEqual(self.b_calls, [('msg', 2), (36, 2)])

    def testSubscriberListRemove(self):
        sl = SubscriberList()

        a = A(self)
        self.b_calls = []
        def b(message, arg):
            self.b_calls.append((message, arg))

        sl.add(a.foo)
        sl.add(b, 3)

        sl.notify(True)
        self.assertEqual(self.a_calls, [(True, None)])
        self.assertEqual(self.b_calls, [(True, 3)])

        sl.remove(a.foo)
        sl.remove(b)

        self.assertEquals(len(list(sl.iteritems())), 0)

        sl.notify(False)
        self.assertEqual(self.a_calls, [(True, None)])
        self.assertEqual(self.b_calls, [(True, 3)])

        # It is OK to remove again.
        sl.remove(a.foo)
        sl.remove(b)

    def test_subscribe_to_self(self):
        # It is important that self.subscribe(event, self.method) does
        # not create a reference loop and interfere with gc.
        ss = SelfSub()
        ss.notify('foo', 'info')
        self.assertEquals(ss.foo_info, 'info')

        wss = weakref.ref(ss)
        self.assertEquals(wss(), ss)
        ss = None
        self.assertEquals(wss(), None)

    def testPublisher(self):
        p = Publisher()

        def add(n):
            self.result = n + 1
        p.subscribe('number', add)
        p.notify('number', 1)
        self.assertEqual(self.result, 2)

        # Exceptions are printed to stderr.
        out, err = grabOutput(p.notify, 'number', 'five')
        self.assertTrue('TypeError' in err)

        p.unsubscribe('number', add)
        p.notify('number', 4)
        self.assertEqual(self.result, 2)

if __name__ == '__main__':
    unittest.main()
