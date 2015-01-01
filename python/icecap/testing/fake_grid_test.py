import unittest
from fake_grid import FakeGrid
from icecap.base.util import pcall

class Servant(object):
    def __init__(self, id):
        self._id = id
        self.nonMethod = 'not a method'

    def id(self):
        return self._id

    def add(self, n):
        return self._id + n

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

        self.assertEqual(repr(proxy), 'log@Log-node1.Log')

        # Check bound method of proxy is not short-circuited to servant.
        proxy_id = proxy.id
        self.assertEqual(proxy_id(), 1)
        env.provide('log', 'Log', Servant(3))
        self.assertEqual(proxy_id(), 3)

        # Check that only methods are available on the proxy.
        self.assertRaises(AttributeError, lambda: proxy._id)
        self.assertRaises(AttributeError, lambda: proxy.fred)
        self.assertRaises(AttributeError, lambda: proxy.begin__id)
        self.assertRaises(AttributeError, lambda: proxy.nonMethod)

        # Check the async call mechanism.
        r = proxy.begin_add(1)
        self.assertEqual(proxy.end_add(r), 4)
        r = proxy.begin_add('')
        self.assertRaises(TypeError, proxy.end_add, r)

        # Find all replicas of a proxy.
        rproxy = env.get_proxy('log@LogGroup')
        replicas = env.replicas(rproxy)
        self.assertEqual([r.id() for r in replicas], [1, 2])

        # Non-replicated proxies have empty replica group.
        self.assertEqual(env.replicas(proxy), [])

        # Use pcall which would make the calls in parallel for real proxies.
        self.assertEqual(pcall(replicas, 'id'), [(1, None), (2, None)])

        # Change servant so that one of two 'add' calls will fail.
        env2.provide('log', 'LogRep', Servant(''))
        results = pcall(replicas, 'add', 1)
        self.assertEqual(results[0], (2, None))
        self.assertEqual(map(type, results[1]), [type(None), TypeError])

if __name__ == '__main__':
    unittest.main()
