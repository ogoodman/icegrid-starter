import unittest
from icecap.ti.fake_grid import FakeGrid
from master import MasterOrSlave, mcall, mcall_f

class Servant(MasterOrSlave):
    def masterNode_async(self, cb, curr=None):
        self.masterNode_f().iceCB(cb)
    def masterNode_f(self):
        return self.assertMaster_f().then(self._masterNode)
    def _masterNode(self, _=None):
        return self._env.serverId().rsplit('-', 1)[-1]

    def findMaster_async(self, cb, curr=None):
        self.findMaster_f().iceCB(cb)
    def isMaster_async(self, cb, curr=None):
        return self.isMaster_f().iceCB(cb)

    def addOne(self, n):
        return n + 1

def server(env):
    env.provide('servant', 'DemoRep', Servant(env))

def badServer(env):
    env.provide('x', 'DemoRep', Servant(env))

class MasterTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        for i in xrange(3):
            grid.addServer('Demo-node%d' % i, server)

        e = grid.env()

        # Choose a master.
        p = e.getProxy('servant@DemoGroup')
        master = mcall(e, p, 'masterNode')

        # Any other proxy should find the same master.
        p2 = e.getProxy('servant@DemoGroup')
        self.assertEqual(master, mcall(e, p2, 'masterNode'))
        
        # Stop and start a slave.
        slave = (int(master[-1]) + 1) % 3
        grid.stopServer('Demo-node%d' % slave)
        ps = e.getProxy('servant@Demo-node%d.DemoRep' % slave)
        self.assertEqual(ps.addOne(6), 7)

        # The master should not have changed.
        self.assertEqual(master, mcall(e, p, 'masterNode'))

        # For coverage.
        mprx = mcall(e, p, 'findMaster')
        self.assertEqual(mprx.ice_getAdapterId(), 'Demo-%s.DemoRep' % master)
        self.assertTrue(mprx.isMaster())

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
        self.assertEqual(new_master, mcall_f(e, p2, 'masterNode').wait())
        self.assertFalse(mprx.isMaster())

    def testSparse(self):
        grid = FakeGrid()
        grid.addServer('Demo-node1', server)
        grid.addServer('Demo-node2', badServer)

        e = grid.env()
        p = e.getProxy('servant@DemoGroup')

        self.assertEqual(mcall(e, p, 'masterNode'), 'node1')

if __name__ == '__main__':
    unittest.main()
