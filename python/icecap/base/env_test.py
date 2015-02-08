import os
import unittest
import Ice
from env import Env, toMostDerived
from icecap import idemo
from icecap.base.antenna import notifyOnline

class EnvTest(unittest.TestCase):
    def test(self):
        env = Env()

        try:
            printer = env.getProxy('printer@DemoGroup')
        except Ice.ConnectionRefusedException:
            print 'WARNING: test skipped, grid not running'
            return

        self.assertEqual(env.serverId(), '')

        # Tests 'provide' and 'serve' on the server.
        self.assertEqual(printer.addOne(1), 2)

        replicas = env.replicas(printer)
        self.assertEqual(len(replicas), 2)

        # Test 'server_id' on the server.
        self.assertEqual(replicas[0].serverId(), 'Demo-node1')

        # For coverage.
        notifyOnline(env, 'Demo-node1')

        self.assertEqual(toMostDerived(printer), printer)

        pp2 = env.getProxy('printer@DemoGroup', type=idemo.PrinterPrx)
        self.assertEqual(pp2.addOne(2), 3)

        grid = env.grid()
        server_ids = grid.getAllServerIds()
        self.assertTrue('Demo-node1' in server_ids)
        self.assertTrue('Demo-node2' in server_ids)
        grid.stopServer('Demo-node1')
        grid.stopServer('Demo-node2')
        grid.stopServer('Demo-node1') # no error if already stopped.

    def testDataDir(self):
        env = Env()
        self.assertTrue(os.path.isdir(env.dataDir()))

if __name__ == '__main__':
    unittest.main()
