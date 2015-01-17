import unittest
import Ice
from env import Env, toMostDerived

class EnvTest(unittest.TestCase):
    def test(self):
        env = Env()

        try:
            printer = env.get_proxy('printer@DemoGroup')
        except Ice.ConnectionRefusedException:
            print 'WARNING: test skipped, grid not running'
            return

        self.assertEqual(env.server_id(), '')

        # Tests 'provide' and 'serve' on the server.
        self.assertEqual(printer.addOne(1), 2)

        replicas = env.replicas(printer)
        self.assertEqual(len(replicas), 2)

        # Test 'server_id' on the server.
        self.assertEqual(replicas[0].serverId(), 'Demo-node1')

        self.assertEqual(toMostDerived(printer), printer)

if __name__ == '__main__':
    unittest.main()
