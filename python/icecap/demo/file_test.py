import unittest
from icecap.ti.fake_grid import FakeGrid
from icecap import idemo
from file import File, addNewReplica

def server(env):
    env.provide('file', 'DemoRep', File(env))

class FileTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()
        grid.addServer('Demo-node1', server)
        grid.addServer('Demo-node2', server)
        env = grid.env()

        fp1 = env.getProxy('file@Demo-node1.DemoRep')
        fp2 = env.getProxy('file@Demo-node2.DemoRep')

        fp1.write('fred', 'hi')
        self.assertEqual(fp2.read('fred'), 'hi')
        self.assertEqual(fp2.list(), ['fred'])

        self.assertRaises(idemo.FileNotFound, fp2.read, 'barney')

        grid.addServer('Demo-node3', server)
        fp3 = env.getProxy('file@Demo-node3.DemoRep')

        # Ideally the existing and new replicas would sort everything
        # out for themselves, but currently they need a little help.
        # We must call addNewReplica to ensure that the existing replicas
        # send updates to the new one, and to replicate all data onto
        # the new one.
        fp = env.getProxy('file@DemoGroup')
        addNewReplica(env, fp, 'node3')

        fp2.write('barney', 'hi fred')
        self.assertEqual(fp3.read('barney'), 'hi fred')

        fp3.write('wilma', 'hi fred')
        self.assertEqual(fp1.read('wilma'), 'hi fred')

        fp3.read('fred')

if __name__ == '__main__':
    unittest.main()
