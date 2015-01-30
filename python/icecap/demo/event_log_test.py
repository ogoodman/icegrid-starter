import json
import unittest
from event_log import EventLog
from icecap.base.util import grabOutput
from icecap.ti.fake_grid import FakeGrid

class Logger(object):
    def __init__(self):
        self._msgs = []

    def log(self, msg):
        self._msgs.append(msg)

    def log2(self, msg, arg):
        self._msgs.append('%s:%s' % (msg, arg))

    def logged(self):
        return self._msgs

def server(env):
    env.provide('logger', 'Demo', Logger())
    env.provide('event_log', 'Demo', EventLog(env, 'events'))

class EventLogTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('Demo-node1', server)
        grid.addServer('Demo-node2', server)

        e = grid.env()

        log_addr = 'logger@Demo-node2.Demo'
        sink_info = json.dumps({'addr': log_addr, 'method': 'log', 'seq': 0})

        elog = e.getProxy('event_log@Demo-node1.Demo')

        elog.append('hello')

        elog.follow('log', sink_info)

        elog.append('goodbye')

        log = e.getProxy(log_addr)
        self.assertEqual(log.logged(), ['hello', 'goodbye'])

        grid.stopServer('Demo-node1')
        grid.stopServer('Demo-node2')
        grid.disable('Demo-node2') # temporarily prevent replication

        elog.append('ping')
        elog.append('gday')

        grid.enable('Demo-node2')

        elog.append('howdy')

        self.assertEqual(log.logged(), ['ping', 'gday', 'howdy'])

        grid.stopServer('Demo-node1')
        grid.stopServer('Demo-node2')
        sink_info = json.dumps({'addr': log_addr, 'method': 'log2', 'arg':'info'})
        elog.follow('log', sink_info)

        elog.append('bonjour')
        self.assertEqual(log.logged(), ['bonjour:info'])

        grid.stopServer('Demo-node1')
        elog.unfollow('log', log_addr)
        elog.unfollow('nothing', log_addr)
        elog.append('yo')
        self.assertEqual(len(log.logged()), 1)


if __name__ == '__main__':
    unittest.main()
