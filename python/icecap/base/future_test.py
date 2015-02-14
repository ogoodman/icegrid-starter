"""Tests for Future."""

import time
import unittest
from thread_pool import ThreadPool
from future import Future, ExceptionList, run_f, prun_f
from icecap.base.util import grabOutput

class FutureTest(unittest.TestCase):
    def setUp(self):
        Future._timeout = 1
        Future._trace_unhandled = False

    def test_prun_f(self):
        pool = ThreadPool(3)
        start = time.time()

        tasks = [(time.sleep, [0.1], {}) for i in xrange(6)]

        results = prun_f(pool, tasks).wait()

        elapsed = time.time() - start
        self.assertTrue(0.15 < elapsed < 0.25)

        self.assertEquals(results, [None]*6)

        future = prun_f(pool, [(lambda: 1+'', [], {})]) # 1+'' will raise a TypeError.
        self.assertRaises(ExceptionList, future.wait)

        # Test results arrive in order of submission (not completion).
        def work(t, i):
            time.sleep(t)
            return i
        tasks = [(work, ((3 - i) / 50., i), {}) for i in xrange(3)]
        results = prun_f(pool, tasks).wait()
        self.assertEquals(results, range(3))

        self.assertEquals(prun_f(pool, []).wait(), [])

        Future._timeout = None
        run_f(pool, time.sleep, .001).wait()

    def testFuture(self):
        # Make sure handling of multiple values is sane.
        r = Future()

        self.fun_args = None
        def fun(*args):
            self.fun_args = args

        r.resolve()
        self.assertEquals(r.wait(), None)
        r.callback(fun)
        self.assertEquals(self.fun_args, ())

        r.resolve(42)
        self.assertEquals(r.wait(), 42)
        r.callback(fun)
        self.assertEquals(self.fun_args, (42,))

        r.resolve('one', 'two')
        self.assertEquals(r.wait(), ('one', 'two'))
        r.callback(fun)
        self.assertEquals(self.fun_args, ('one', 'two'))

        # We can also handle exceptions.
        def bad():
            x = {}['key']

        r = Future()
        r.errback(fun)
        r.run(bad)

        self.assertRaises(KeyError, r.wait)
        self.assertTrue(isinstance(self.fun_args[0], KeyError))

        r = Future()
        r.run(bad)
        r.errback(fun)

        self.assertTrue(isinstance(self.fun_args[0], KeyError))

        # A future may be created already resolved.
        r = Future(None)
        self.assertEquals(r.wait(), None)

        f = Future()
        self.assertRaises(Exception, f.wait, timeout=0.01)

        f = Future()
        f.callback(fun)
        f.run(lambda: (1, 2, 3))
        self.assertEqual(self.fun_args, (1, 2, 3))

    def testThen(self):
        def add(x, y):
            return x + y

        # simple case
        f = Future()
        g = f.then(add, 1)
        f.resolve(1)
        self.assertEquals(g.wait(), 2)

        # f already resolved
        f = Future(2)
        g = f.then(add, 2)
        self.assertEquals(g.wait(), 4)

        # exception in f
        f = Future()
        g = f.then(add, 3)
        f.error(ValueError('whatever'))
        self.assertRaises(ValueError, g.wait)

        # exception in chained call
        f = Future()
        g = f.then(add, '')
        f.resolve(1)
        self.assertRaises(TypeError, g.wait)

        # chaining futures
        f = Future()
        g = Future()
        f.resolve(g)
        g.resolve(2)
        self.assertEquals(f.wait(), 2)

        # chain with already resolved
        f = Future()
        g = Future(2)
        f.resolve(g)
        self.assertEquals(f.wait(), 2)
        
        # resolve chained with exception
        f = Future()
        g = Future()
        f.resolve(g)
        g.error(KeyError('fred'))
        self.assertRaises(KeyError, f.wait)

        # chained function returning future
        r = Future()
        def fun(n):
            assert n == 5
            return r
        f = Future()
        g = f.then(fun)
        # fun will be passed 5 and return r
        # whose value will become the value of g.
        f.resolve(5)
        r.resolve('x')
        self.assertEquals(g.wait(), 'x')

    def testDiagnostic(self):
        def tryToLoseAnException():
            f = Future()
            f.error(KeyError(42))

        err = grabOutput(tryToLoseAnException)[1]
        self.assertTrue(err.startswith('Unhandled exception'))
        self.assertTrue('KeyError' in err)
        self.assertFalse('tryToLoseAnException' in err)

        Future._trace_unhandled = True
        err = grabOutput(tryToLoseAnException)[1] # includes traceback to the error.
        self.assertTrue('tryToLoseAnException' in err)

if __name__ == '__main__':
    unittest.main()
