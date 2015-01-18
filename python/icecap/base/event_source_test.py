import json
import os
import unittest
from event_source import EventSource
from icecap.base.util import grabOutput
from icecap.ti.fake_grid import FakeGrid

class Logger(object):
    def __init__(self):
        self._msgs = []

    def log(self, msg):
        self._msgs.append(msg)

    def log2(self, msg, arg):
        self._msgs.append(msg + ':' + arg)

    def logged(self):
        return self._msgs

def server(env):
    env.provide('logger', 'Demo', Logger())
    env.provide('events', 'Demo', EventSource(env, 'events'))

class EventSourceTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('Demo-node', server)

        e = grid.env()

        log_addr = 'logger@Demo-node.Demo'
        sink_info = json.dumps({'addr': log_addr, 'method': 'log'})

        ev = e.getProxy('events@Demo-node.Demo')
        ev.follow('foo', sink_info)

        ev.send('foo', 'hello')
        ev.send('bar', 'goodbye')

        log = e.getProxy(log_addr)
        self.assertEqual(log.logged(), ['hello'])

        ev.unfollow('foo', log_addr)
        ev.send('foo', 'ping')

        ev.unfollow('baz', log_addr) # not an error

        log = e.getProxy(log_addr)
        self.assertEqual(log.logged(), ['hello'])

        sink_info2 = json.dumps({'addr': log_addr, 'method': 'log2', 'arg':'bar'})
        ev.follow('bar', sink_info2)

        # Subscription is persistent.
        grid.stopServer('Demo-node')

        ev.send('bar', 'gday')
        self.assertEqual(log.logged(), ['gday:bar'])

        # When send causes an exception it will appear on server stderr
        sink_info2 = json.dumps({'addr': log_addr, 'method': 'log2'})
        ev.follow('bar', sink_info2)

        out, err = grabOutput(ev.send, 'bar', 'ciao')
        self.assertTrue('TypeError' in err) # log2() not passed enough args.

        # For coverage.
        grid.stopServer('Demo-node')
        ev.unfollow('baz', log_addr)


if __name__ == '__main__':
    unittest.main()
