import sys
import unittest
from icecap.base.master import mcall
from icecap.base.util import grabOutput
from icecap.ti.fake_grid import FakeGrid
from icecap.demo import server

class PrinterTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('Demo-node1', server.init)

        env = grid.env()
        proxy = env.getProxy('printer@Demo-node1.Demo')
        self.assertEqual(proxy.addOne(5), 6)
        self.assertEqual(proxy.serverId(), 'Demo-node1')

        proxy = env.getProxy('printer@DemoGroup')
        self.assertEqual(proxy.addOne(7), 8)

        output = grabOutput(proxy.printString, 'Hello')
        self.assertEqual(output, ('Hello\n', ''))

        self.assertTrue(type(proxy.getRand()) in (int, long))

        self.assertEqual(mcall(env, proxy, 'masterNode'), 'node1')

if __name__ == '__main__':
    unittest.main()
