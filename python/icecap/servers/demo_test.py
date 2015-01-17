import sys
import unittest
from icecap.base.util import grabOutput
from icecap.ti.fake_grid import FakeGrid
from demo import setup as setupServer

class DemoTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.add_server('Demo-node1', setupServer)

        env = grid.env()
        proxy = env.get_proxy('printer@Demo-node1.Demo')
        self.assertEqual(proxy.addOne(5), 6)
        self.assertEqual(proxy.serverId(), 'Demo-node1')

        proxy = env.get_proxy('printer@DemoGroup')
        self.assertEqual(proxy.addOne(7), 8)

        output = grabOutput(proxy.printString, 'Hello')
        self.assertEqual(output, ('Hello\n', ''))

        self.assertTrue(type(proxy.getRand()) in (int, long))

if __name__ == '__main__':
    unittest.main()
