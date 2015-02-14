"""A test for ThreadPool."""

import time
import unittest
from thread_pool import ThreadPool
from icecap.base.future import Future
from icecap.base.util import grabOutput

class ThreadPoolTest(unittest.TestCase):
    def test(self):
        pool = ThreadPool(3)
        start = time.time()

        # Start 3 tasks and queue 3.
        for i in xrange(6):
            pool.do(time.sleep, 0.1)
        pool.join()

        elapsed = time.time() - start
        self.assertTrue(0.15 < elapsed < 0.25)

    def testDiagnostic(self):
        pool = ThreadPool(1)

        def generateError():
            pool.do(lambda: 1+'')
            f = Future()
            pool.do(f.resolve)
            f.wait()

        err = grabOutput(generateError)[1]
        self.assertTrue('TypeError' in err)

if __name__ == '__main__':
    unittest.main()
