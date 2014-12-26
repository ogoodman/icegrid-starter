import sys
import unittest
from cStringIO import StringIO
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

        try:
            keep_stdout, sys.stdout = sys.stdout, StringIO()
            proxy.printString('Hello')
        finally:
            grabbed, sys.stdout = sys.stdout, keep_stdout
        self.assertEqual(grabbed.getvalue(), 'Hello\n')

if __name__ == '__main__':
    unittest.main()
