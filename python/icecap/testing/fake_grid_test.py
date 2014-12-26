import unittest
from fake_grid import FakeGrid

class Servant(object):
    def __init__(self, id):
        self._id = id

    def id(self):
        return self._id

class FakeEnvTest(unittest.TestCase):
    def test(self):
        grid = FakeGrid()

        # Provide and then look up a servant on a normal adapter.
        env = grid.env('Log-node1')
        env.provide('log', 'Log', Servant(1))

        proxy = env.get_proxy('log@Log-node1.Log')
        self.assertEqual(proxy.id(), 1)

        env2 = grid.env('Log-node2')

        # Test round-robin: usually replicas would be equivalent.
        env.provide('log', 'LogRep', Servant(1))
        env2.provide('log', 'LogRep', Servant(2))

        ids = [env.get_proxy('log@LogGroup').id() for i in xrange(3)]
        self.assertEqual(ids, [1, 2, 1])

if __name__ == '__main__':
    unittest.main()
