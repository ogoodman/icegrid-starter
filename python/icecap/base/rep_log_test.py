"""Tests for the data_log module."""

import unittest
from icecap.ti.fake_grid import FakeGrid
from rep_log import RepLog

class Servant(object):
    def __init__(self):
        self._calls = []

    def func(self, arg):
        self._calls.append(arg)

    def f2(self, a1, a2):
        self._calls.append('%s:%s' % (a1, a2))

    def calls(self):
        return self._calls

def server(env):
    env.provide('servant', 'Server', Servant())

class RepLogTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('Server-node1', server)
        grid.addServer('Server-node2', server)

        env = grid.env('Log-node1')
        log = RepLog(env, 'test_log')

        addr1 = 'servant@Server-node1.Server'
        self.assertEqual(log.getSink(addr1), None)
        sink1 = {'addr': addr1, 'method': 'func', 'pos': 0}
        self.assertTrue(log.addSink(sink1))
        self.assertFalse(log.addSink(sink1))

        log.update(addr1) # no-op for empty log.

        # Sinks added when log is empty start at 0 automatically.
        log.append('one')
        pr1 = env.getProxy(addr1)
        self.assertEqual(pr1.calls(), ['one'])

        pos1 = log.size()
        self.assertTrue(log.removeSink(addr1))
        self.assertFalse(log.removeSink(addr1))
        log.append('two')
        self.assertEqual(log.size(), 2)
        self.assertEqual(pr1.calls(), ['one'])

        # Re-add sink1 at previous position
        sink1['pos'] = pos1
        log.addSink(sink1)
        log.update(addr1)
        self.assertEqual(pr1.calls(), ['one', 'two'])

        addr2 = 'servant@Server-node2.Server'
        pr2 = env.getProxy(addr2)
        self.assertEqual(pr2.calls(), [])

        grid.disable('Server-node2')
        grid.stopServer('Server-node2')

        sink2 = {'addr': addr2, 'method': 'func', 'pos': 0}
        log.addSink(sink2)
        log.update(addr2)
        self.assertEqual(log.getSeq(addr2), 0)

        self.assertRaises(KeyError, log.update, 'nonesuch@Server-node3.Server')

        log.removeSink(addr1)
        sink1 = {'addr': addr1, 'method': 'f2', 'arg': 'opt-arg', 'pos': log.size()}
        log.addSink(sink1)
        log.append('three')
        self.assertEqual(pr1.calls(), ['one', 'two', 'three:opt-arg'])

        # RepLog is persistent.
        log = RepLog(env, 'test_log')
        grid.enable('Server-node2')
        log.update(addr2) # position and sink are remembered
        self.assertEqual(pr2.calls(), ['one', 'two', 'three'])

        log = RepLog(env, 'test_log')
        log.setSeq(addr2, 2)
        log.update(addr2)
        self.assertEqual(pr2.calls(), ['one', 'two', 'three', 'three'])

        log = RepLog(env, 'test_log')
        log.removeSink(addr2)
        log.append('four')
        self.assertEqual(pr1.calls(), ['one', 'two', 'three:opt-arg', 'four:opt-arg'])
        self.assertEqual(pr2.calls(), ['one', 'two', 'three', 'three'])


if __name__ == '__main__':
    unittest.main()
