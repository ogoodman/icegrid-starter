import os
import unittest
from icecap.base import util
from icecap.ti.fake_grid import FakeGrid

class UtilTest(unittest.TestCase):
    def test(self):
        self.assertTrue('slice' in os.listdir(util.appRoot()))

        app_root_fn = util.importSymbol('icecap.base.util.appRoot')
        self.assertEqual(app_root_fn, util.appRoot)

        # grabOutput captures stdout and stderr for the duration of a call.
        def echo(msg):
            print msg
        so, se = util.grabOutput(echo, 'Hi')
        self.assertEqual((so, se), ('Hi\n', ''))

        # Exceptions are trapped and traceback reported from stderr.
        so, se = util.grabOutput('not a func', 'arg')
        self.assertEqual(so, '')
        self.assertTrue('TypeError' in se)

    def testGetAddr(self):
        grid = FakeGrid()
        env = grid.env()

        addr = 'file@Demo-node1.DemoRep'
        prx = env.getProxy(addr)
        self.assertEqual(util.getAddr(prx), addr)
        self.assertEqual(util.getAddr(addr), addr)
        self.assertEqual(util.getAddr(unicode(addr)), addr)

        self.assertEqual(util.getNode(prx), 'node1')

        gprx = env.getProxy('file@DemoGroup')
        self.assertEqual(util.getReplicaAddr(gprx, 'node1'), 'file@Demo-node1.DemoRep')

if __name__ == '__main__':
    unittest.main()
