import unittest
from icecap.ti.fake_grid import FakeGrid
from icecap import idemo
from file import File

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

        self.assertRaises(idemo.FileNotFound, fp2.read, 'barney')

if __name__ == '__main__':
    unittest.main()
