import unittest
from icecap.testing.fake_grid import FakeGrid
from icecap.servers.printer import setup as server
from master import mcall

class MasterTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        for i in xrange(3):
            grid.add_server('Printer-node%d' % i, server)

        e = grid.env()

        # Start a server.
        p1 = e.get_proxy('printer@Printer-node1.Printer')
        self.assertTrue(p1.addOne(5), 6)

        # The master won't always be the first started server.
        p = e.get_proxy('printer@PrinterGroup')
        master = mcall(e, p, 'masterNode')

        # Any other proxy should find the same master.
        p2 = e.get_proxy('printer@PrinterGroup')
        self.assertEqual(master, mcall(e, p2, 'masterNode'))
        
        # Stop and start a slave.
        slave = (int(master[-1]) + 1) % 3
        grid.stop_server('Printer-node%d' % slave)
        ps = e.get_proxy('printer@Printer-node%d.Printer' % slave)
        self.assertEqual(ps.addOne(6), 7)

        # The master should not have changed.
        self.assertEqual(master, mcall(e, p, 'masterNode'))

        # The master may change when it is stopped; keep trying until it does.
        for i in xrange(100):
            grid.stop_server('Printer-%s' % master)
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

        

if __name__ == '__main__':
    unittest.main()
