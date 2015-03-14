import unittest
from icecap.base.antenna import notifyOnline
from icecap.base.master import mcall
from icecap.base.util import getAddr
from icecap.ti.fake_grid import FakeGrid
from icecap import ibase, istorage
from small_fs import server
from data_manager import server as dm_server
from icecap.storage.data_client import DataClient

class FileTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('DataManager-node1', dm_server)
        grid.addServer('DataManager-node2', dm_server)
        grid.addServer('SmallFS-node1', server)
        grid.addServer('SmallFS-node2', server)

        env = grid.env()
        fp = env.getProxy('file@SmallFSGroup')
        dc = DataClient(env, fp)
        fp1 = env.getProxy('file@SmallFS-node1.SmallFSRep')
        fp2 = env.getProxy('file@SmallFS-node2.SmallFSRep')

        dc.write('fred', 'hi')

        self.assertEqual(dc.list(''), ['fred'])
        self.assertEqual(dc.read('fred'), 'hi')

        self.assertEqual(fp2.listRep(), ['fred'])
        self.assertEqual(fp2.readRep('fred'), 'hi')

        self.assertRaises(istorage.FileNotFound, fp2.readRep, 'barney')

        grid.stopServer('SmallFS-node2')
        grid.disable('SmallFS-node2')

        dc.write('fred', 'lo') # node1 becomes master
        dc.write('barney', 'dino')

        grid.enable('SmallFS-node2')

        # Starting SmallFS-node2 should trigger updates from SmallFS-node1.
        self.assertEqual(fp2.readRep('fred'), 'lo')

        fp1.assertMasterFor('')
        self.assertRaises(ibase.NotMaster, fp2.assertMasterFor, '')

        # Starting SmallFS-node3 will cause a full sync from SmallFS-node1.
        grid.addServer('SmallFS-node3', server)

        grid.stopServer('SmallFS-node1')

        fp = env.getProxy('file@SmallFSGroup')
        dc = DataClient(env, fp)
        self.assertEqual(set(dc.list('')), {'fred', 'barney'})
        dc.write('fred', 'go') # force node3 to be populated.

        fp3 = env.getProxy('file@SmallFS-node3.SmallFSRep')
        self.assertEqual(set(fp3.listRep()), {'fred', 'barney'})
        self.assertEqual(fp3.readRep('fred'), 'go')

        fp2.writeRep('barney', 'hi fred')
        self.assertEqual(fp3.readRep('barney'), 'hi fred')

        fp3.writeRep('wilma', 'hi fred')
        self.assertEqual(fp1.readRep('wilma'), 'hi fred')

        fp3.readRep('fred')

        # For coverage.
        notifyOnline(env, 'Other-node1')

        dm = env.getProxy('file@DataManagerGroup')
        mcall(env, dm, 'remove', getAddr(fp3))
        mcall(env, dm, 'remove', getAddr(fp3))

if __name__ == '__main__':
    unittest.main()
