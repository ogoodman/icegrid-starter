import unittest
from icecap.ti.fake_grid import FakeGrid
from icecap.servers import demo
from icecap.demo.printer import Printer
from master import mcall

class MasterTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        for i in xrange(3):
            grid.addServer('Demo-node%d' % i, demo.setup)

        e = grid.env()

        # Start a server.
        p1 = e.getProxy('printer@Demo-node1.Demo')
        self.assertTrue(p1.addOne(5), 6)

        # The master won't always be the first started server.
        p = e.getProxy('printer@DemoGroup')
        master = mcall(e, p, 'masterNode')

        # Any other proxy should find the same master.
        p2 = e.getProxy('printer@DemoGroup')
        self.assertEqual(master, mcall(e, p2, 'masterNode'))
        
        # Stop and start a slave.
        slave = (int(master[-1]) + 1) % 3
        grid.stopServer('Demo-node%d' % slave)
        ps = e.getProxy('printer@Demo-node%d.Demo' % slave)
        self.assertEqual(ps.addOne(6), 7)

        # The master should not have changed.
        self.assertEqual(master, mcall(e, p, 'masterNode'))

        # For coverage of MasterOrSlave.findMaster.
        mprx = mcall(e, p, 'findMaster')
        self.assertEqual(mprx.ice_getAdapterId(), 'Demo-%s.DemoRep' % master)

        # The master may change when it is stopped; keep trying until it does.
        for i in xrange(100):
            grid.stopServer('Demo-%s' % master)
            new_master = mcall(e, p, 'masterNode')
            if new_master != master:
                break
        else:
            # There is a small chance of failing here, even if things are working ok.
            # We really need to put random number generation into Env and make
            # FakeEnv give the values we need to construct a deterministic test.
            self.assertFalse('Master should have changed and did not.')

        # Make sure p2 tracks the change.
        self.assertEqual(new_master, mcall(e, p2, 'masterNode'))
        
    def testSparse(self):
        def badServer(env):
            env.provide('x', 'DemoRep', Printer(env))

        grid = FakeGrid()
        grid.addServer('Demo-node1', demo.setup)
        grid.addServer('Demo-node2', badServer)

        e = grid.env()
        p = e.getProxy('printer@DemoGroup')

        self.assertEqual(mcall(e, p, 'masterNode'), 'node1')

if __name__ == '__main__':
    unittest.main()
