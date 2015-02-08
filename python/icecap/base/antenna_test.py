import unittest
from icecap.ti.fake_grid import FakeGrid
from icecap.base.util import grabOutput
from antenna import Antenna, notifyOnline

class Ping(object):
    def ping(self):
        pass

def onOnline(server_id):
    print 'online', server_id

def server(env):
    env.provide('ping', 'Demo', Ping())
    env.provide('antenna', 'DemoRep', Antenna(env))
    env.subscribe('online', onOnline)

class AntennaTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        for i in xrange(3):
            grid.addServer('Demo-node%d' % i, server)

        e = grid.env()
        p0 = e.getProxy('ping@Demo-node0.Demo')
        self.assertFalse(grid.serverIsActive('Demo-node0'))
        p0.ping()
        self.assertTrue(grid.serverIsActive('Demo-node0'))
        self.assertFalse(grid.serverIsActive('Demo-node1'))

        out, err = grabOutput(notifyOnline, e, 'Demo-node1')
        self.assertTrue('online Demo-node1' in out)

if __name__ == '__main__':
    unittest.main()
