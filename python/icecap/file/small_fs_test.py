import unittest
from icecap.base.antenna import notifyOnline
from icecap.ti.fake_grid import FakeGrid
from icecap import idemo
from small_fs import server

class FileTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('SmallFS-node1', server)
        grid.addServer('SmallFS-node2', server)
        env = grid.env()

        fp1 = env.getProxy('file@SmallFS-node1.SmallFSRep')
        fp2 = env.getProxy('file@SmallFS-node2.SmallFSRep')

        fp1.write('fred', 'hi')
        self.assertEqual(fp2.read('fred'), 'hi')
        self.assertEqual(fp2.list(), ['fred'])

        self.assertRaises(idemo.FileNotFound, fp2.read, 'barney')

        grid.stopServer('SmallFS-node2')
        grid.disable('SmallFS-node2')

        fp1.write('fred', 'lo')

        grid.enable('SmallFS-node2')

        # Starting SmallFS-node1 should trigger updates from SmallFS-node2.
        self.assertEqual(fp2.read('fred'), 'lo')

        grid.addServer('SmallFS-node3', server)
        fp3 = env.getProxy('file@SmallFS-node3.SmallFSRep')
        self.assertEqual(fp3.list(), ['fred'])
        self.assertEqual(fp3.read('fred'), 'lo')

        fp2.write('barney', 'hi fred')
        self.assertEqual(fp3.read('barney'), 'hi fred')

        fp3.write('wilma', 'hi fred')
        self.assertEqual(fp1.read('wilma'), 'hi fred')

        fp3.read('fred')

        # For coverage (of _onOnline).
        notifyOnline(env, 'Other-node1')

if __name__ == '__main__':
    unittest.main()
