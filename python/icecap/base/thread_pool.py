"""``ThreadPool`` implements a *concurrency provider* interface. 

This consists of a ``.do`` method with signature ``.do(func, *args, **kw)``. 
An implementation is expected (at some point in time) to make the call ``func(*args, **kw)``. 
It may, for example:

* call *func* immediately (*synchronous*),
* call *func* in a thread (*threaded*), or
* schedule *func* to be called by a reactor (*co-operative multi-tasking*).

The synchronous case can be useful in unit tests.
"""

import atexit
import threading
import traceback

class FIFO(object):
    """A ThreadPool first-in-first-out queue strategy.

    This is the default strategy for a ThreadPool. 

    Tasks are started in the order they are added. This has the defect
    that if the thread pool is shared and one client adds a large
    number of tasks, any other client will have to wait for all of
    those tasks to be started before any subsequently added task can begin.
    """
    def __init__(self):
        self._queue = []

    def put(self, work):
        self._queue.append(work)

    def get(self):
        if self._queue:
            return self._queue.pop(0)
        return None

    def __len__(self):
        return len(self._queue)

class ThreadPool(object):
    """A ThreadPool.

    Usage::

        pool = ThreadPool(n) # make a pool with up to n threads.

        pool.do(fun, a1, a2, key='K1') # run fun(a1, a2, key='K1') in a thread

        # To get the result as a Future, use the call function:
        f = call(pool, fun, a1, a2, key='K1')

    Adding a task causes a new thread to be started if there are
    fewer than *n* threads and they are all currently busy.
    If there are *n* threads, all busy, the task is queued until
    a thread becomes available. 

    If multiple tasks are queued they may be re-ordered according by
    the configured queue. The default queue strategy is simply first-in
    first-out.

    If supplied, the queue strategy must be an object with interface::

        queue.put(work) # work is a tuple (func, args, kwargs)
        queue.get()     # returns a previous work item or None

    To free up resources you can do::

        pool.release() # tell pool to shut down when all work is done
        pool.join() # tell pool to shut down and wait until all work is done.

    If you do nothing, ``pool.join()`` will be called in an ``atexit`` handler.

    :param n: maximum number of threads to start.
    :param queue: a queue object such as a FIFO (the default) or RoundRobin instance
    """
    def __init__(self, n, queue=None):
        self._queue = FIFO() if queue is None else queue
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._n = n
        self._threads = []
        self._idle = 0
        self._done = False

        atexit.register(self.join)

    def _addThread(self):
        """Adds a new worker thread to the pool."""
        thread = threading.Thread(target=self._process)
        thread.setDaemon(True)
        self._threads.append(thread)
        thread.start()

    def _process(self):
        """The main-loop for each worker thread."""
        while True:
            # Get some work to do or wait for some.
            with self._lock:
                while True:
                    work = self._queue.get()
                    if work:
                        break
                    if self._done:
                        return
                    self._idle += 1
                    self._cond.wait()
                    self._idle -= 1
                func, args, kwargs = work

            # Do the work.
            try:
                func(*args, **kwargs)
            except:
                traceback.print_exc()

    def do(self, func, *args, **kwargs):
        """Call func in the next available thread.

        Results are discarded. Any exception raised will cause a traceback to be printed
        to ``sys.stderr``.

        :param func: a callable
        :param args: variable argument list to pass to *func*
        :param kw: any keyword arguments to pass to *func*
        """
        with self._lock:
            self._queue.put((func, args, kwargs))
            if len(self._threads) < self._n and self._idle < len(self._queue):
                self._addThread()
            self._cond.notifyAll()

    def release(self):
        """Tells all threads exit as soon as all queued work is done.

        This call does not block.
        """
        with self._lock:
            self._done = True
            self._cond.notifyAll()

    def join(self):
        """Tells all threads to exit and wait until all work is done.
        
        This call blocks until all threads have been joined.
        """
        self.release()
        for thread in self._threads:
            thread.join()
            with self._lock:
                self._threads.remove(thread)
