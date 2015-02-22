import unittest
from icecap.base.antenna import notifyOnline
from icecap.base.master import mcall
from icecap.ti.fake_grid import FakeGrid
from icecap import idemo
from small_fs import server

class FileTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('SmallFS-node1', server)
        grid.addServer('SmallFS-node2', server)
        env = grid.env()

        fp = env.getProxy('file@SmallFSGroup')
        fp1 = env.getProxy('file@SmallFS-node1.SmallFSRep')
        fp2 = env.getProxy('file@SmallFS-node2.SmallFSRep')

        mcall(env, fp, 'write', 'fred', 'hi')
        self.assertEqual(mcall(env, fp, 'list'), ['fred'])
        self.assertEqual(mcall(env, fp, 'read', 'fred'), 'hi')

        self.assertEqual(fp2.listRep(), ['fred'])
        self.assertEqual(fp2.readRep('fred'), 'hi')

        self.assertRaises(idemo.FileNotFound, fp2.readRep, 'barney')

        grid.stopServer('SmallFS-node2')
        grid.disable('SmallFS-node2')

        mcall(env, fp, 'write', 'fred', 'lo') # node1 becomes master

        grid.enable('SmallFS-node2')

        # Starting SmallFS-node2 should trigger updates from SmallFS-node1.
        self.assertEqual(fp2.readRep('fred'), 'lo')

        # Starting SmallFS-node3 will cause a full sync from SmallFS-node1.
        grid.addServer('SmallFS-node3', server)
        fp3 = env.getProxy('file@SmallFS-node3.SmallFSRep')
        self.assertEqual(fp3.listRep(), ['fred'])
        self.assertEqual(fp3.readRep('fred'), 'lo')

        fp2.writeRep('barney', 'hi fred')
        self.assertEqual(fp3.readRep('barney'), 'hi fred')

        fp3.writeRep('wilma', 'hi fred')
        self.assertEqual(fp1.readRep('wilma'), 'hi fred')

        fp3.readRep('fred')

        # For coverage (of _onOnline).
        notifyOnline(env, 'Other-node1')

if __name__ == '__main__':
    unittest.main()
