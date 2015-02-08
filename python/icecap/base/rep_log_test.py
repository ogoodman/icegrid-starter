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
        sink1 = {'addr': addr1, 'method': 'func'}
        self.assertTrue(log.addSink(sink1))
        self.assertEqual(log.getSink(addr1), sink1)
        self.assertFalse(log.addSink(sink1))

        log.update(addr1) # no-op for empty log.

        # Sinks added when log is empty start at 0 automatically.
        log.append('one')
        pr1 = env.getProxy(addr1)
        self.assertEqual(pr1.calls(), ['one'])

        self.assertTrue(log.removeSink(addr1))
        self.assertFalse(log.removeSink(addr1))
        log.append('two')
        self.assertEqual(log.size(), 2)
        self.assertEqual(pr1.calls(), ['one'])

        # Sinks added to a non-empty log don't start automaticall.
        addr2 = 'servant@Server-node2.Server'
        sink2 = {'addr': addr2, 'method': 'func'}
        log.addSink(sink2)
        log.update(addr2)
        pr2 = env.getProxy(addr2)
        self.assertEqual(pr2.calls(), [])

        # A re-added sink continues from where it was.
        log.addSink(sink1)
        log.update(addr1)
        self.assertEqual(pr1.calls(), ['one', 'two'])

        grid.disable('Server-node2')
        grid.stopServer('Server-node2')
        log.setSeq(addr2, 0) # start pushing to addr2
        log.update(addr2)

        log.update('nonesuch@Server-node3.Server') # no-op

        sink1 = {'addr': addr1, 'method': 'f2', 'arg': 'opt-arg'}
        log.removeSink(addr1)
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
        log.removeSeq(addr2)
        log.append('four')
        self.assertEqual(pr1.calls(), ['one', 'two', 'three:opt-arg', 'four:opt-arg'])
        self.assertEqual(pr2.calls(), ['one', 'two', 'three', 'three'])


if __name__ == '__main__':
    unittest.main()
