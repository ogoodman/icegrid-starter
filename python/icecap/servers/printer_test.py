import sys
import unittest
from icecap.base.util import grabOutput
from icecap.testing.fake_grid import FakeGrid
from printer import setup as setupServer

class PrinterTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        setupServer(grid.env('Printer-node1'))

        env = grid.env()
        proxy = env.get_proxy('printer@Printer-node1.Printer')
        self.assertEqual(proxy.addOne(5), 6)

        proxy = env.get_proxy('printer@PrinterGroup')
        self.assertEqual(proxy.addOne(7), 8)

        output = grabOutput(proxy.printString, 'Hello')
        self.assertEqual(output, ('Hello\n', ''))

        self.assertTrue(type(proxy.getRand()) in (int, long))

if __name__ == '__main__':
    unittest.main()
