import sys
import threading
import time
import traceback

def rvToArgTup(result):
    """Converts a return value to a tuple suitable for passing as ``*args``.

    Example::

        result = callSomething()
        callback(*rvToArgTup(result))

    * If result is ``None`` this does ``callback()``,
    * if result is not a tuple this does ``callback(result)``, and
    * if result is a tuple this does ``callback(*result)``.

    :param result: anything
    """
    if result is None:
        return ()
    if type(result) is tuple:
        return result
    return (result,)

def argTupToRv(tup):
    """Converts a tuple representing a return value to its usual form.

    Tuples are usually only returned from functions when returning multiple values.
    Functions which return nothing, normally return ``None`` while functions
    return a single value by itself. 

    * If tup is ``()`` this returns ``None``,
    * if tup is ``(value,)`` it returns ``value``, and
    * if tup is anything bigger, it returns it unchanged.

    :param tup: a tuple
    """
    if len(tup) == 0:
        return None
    if len(tup) == 1:
        return tup[0]
    return tup

class Future(object):
    """A ``Future`` can be used to retrieve results from calls made asynchronously.

    Given::

        def async():
            result = Future()

            def work():
                try:
                    result.resolve(some_big_calc())
                except Exception, e:
                    result.error(e)

            Thread(target=work).start()
            return result

    We can retrieve the results of ``some_big_calc()`` synchronously::

            f = async()
            r = f.wait() # blocks until some_big_calc() finishes

    (if ``result.error()`` was called this will raise the exception)
    or via callbacks::

        def handler(r):
            # do something with r.
        def errh(exc):
            # handle an error.

        f = async()
        f.callback(handler, errh)

    which will cause ``handler`` or ``errh`` to be called eventually.

    :param result: (optional) creates ``Future`` already resolved if supplied
    """
    _timeout = None
    _trace_unhandled = False

    def __init__(self, *result):
        self._cond = threading.Condition()
        self._result = () if result == (None,) else result or None
        self._exc = None
        self._cb = None
        self._eb = None
        self._tb = None

    def callback(self, cb, eb=None):
        """Set a function to receive the result.

        The callback function *cb* is passed the same argument
        list that ``Future.resolve`` is called with.
        Any error callback *eb* will always be called with a
        single exception argument.

        :param cb: a callback function
        :param eb: an error handling callback
        """
        with self._cond:
            if self._result is not None:
                cb(*self._result)
            else:
                self._cb = cb
        if eb is not None:
            self.errback(eb)

    def errback(self, eb):
        """Set a function to receive any exception.

        In the event that ``Future.error()`` is called, its argument,
        which is expected to be an exception, is passed to *eb*.

        This can also be set by the ``.callback()`` method.

        :param eb: an error handling callback
        """
        with self._cond:
            if self._exc is None:
                self._eb = eb
            else:
                eb(self._exc)
                self._eb = True

    def iceCB(self, cb):
        """Provide an Ice callback object to receive the result or exception.

        This is simply a shortcut for::

            self.callbacks(cb.ice_response, cb.ice_exception)

        :param cb: an Ice callback object
        """
        self.callback(cb.ice_response, cb.ice_exception)

    def wait(self, timeout=None):
        """Wait until the result becomes available and return it.

        If ``Future.resolve(*args)`` is called in another thread, or has
        already been called, this call will return a result as follows:

        * when resolved as ``.resolve()`` the result is ``None``,
        * when resolved as ``.resolve(a)`` the result is just ``a``,
        * when resolved as ``.resolve(a, b, ...)`` the result is ``(a, b, ...)``.

        If ``Future.error(exc)`` is called in another thread, or has
        already been called, this call will raise the exception.

        :param timeout: how long to wait for a result (``None`` means indefinitely)
        """
        with self._cond:
            if self._eb is None:
                self._eb = lambda e: None
            timeout = timeout or self._timeout
            if timeout:
                limit = time.time() + timeout
            while self._result is None and self._exc is None:
                if timeout:
                    now = time.time()
                    if now >= limit:
                        raise Exception('Future.wait() timed out after %s.' % timeout)
                    self._cond.wait(limit - now)
                else:
                    self._cond.wait()
            if self._exc:
                raise self._exc

            # Calling with *args, and returning are subtly different.
            return argTupToRv(self._result)

    def resolve(self, *result):
        """Provide the result.

        If called with a single ``Future`` argument, the eventual result or
        error of that will become our result or error.

        :param result: the values to return from ``.wait()`` or pass to a callback
        """
        if len(result) == 1 and type(result[0]) is Future:
            resolver = result[0]
            resolver.callback(self.resolve, self.error)
            return
        with self._cond:
            self._result = result
            self._cond.notifyAll()
            cb = self._cb
        if cb is not None:
            cb(*result)

    def error(self, exc):
        """Provide an exception.

        :param exc: the exception to raise in ``.wait()`` or pass to an error handler
        """
        with self._cond:
            self._exc = exc
            if self._trace_unhandled:
                self._tb = traceback.format_stack()
            self._cond.notifyAll()
            eb = self._eb
        if eb is not None:
            eb(self._exc)

    def run(self, func, *args, **kw):
        """Convenience function to run func and set the result or exception.

        If *func* returns normally its return value(s) are passed to ``Future.resolve``
        as follows:

        * ``None`` results in the call ``.resolve()``,
        * any *non-tuple* (or *1-tuple*) result ``r`` is passed as ``.resolve(r)``,
        * any *tuple* result ``r`` (of length 2 or more) is unpacked as ``.resolve(*r)``.

        If *func* raises an exception it is passed to ``Future.error``.

        :param func: a callable
        :param args: variable argument list to pass to *func*
        :param kw: any keyword arguments to pass to *func*
        """
        try:
            r = func(*args, **kw)
            self.resolve(*rvToArgTup(r))
        except Exception, e:
            self.error(e)

    def then(self, func, *args, **kw):
        """Make a new Future which calls func with the result of this one.

        When this Future is resolved, the result and args are
        concatenated to form the argument list for func.
        If this Future resolves with an exception, it is passed
        through to the new Future.

        :param func: a callable to call with this Future's result
        :param args: additional arguments for *func*
        :param kw: keyword arguments to pass to *func*
        """
        new = Future()
        def chain(*result):
            new.run(func, *(result + args), **kw)
        self.callback(chain, new.error)
        return new

    def __del__(self):
        """Prints a message to ``sys.stderr`` if an exception was set but never handled.

        By default this only prints a message and the exception. To get a traceback
        identifying where the exception was added, set ``Future._trace_unhandled = True``.
        Note that this could affect performance though.
        """
        if self._exc is not None and self._eb is None:
            print >>sys.stderr, 'Unhandled exception in Future: %r' % self._exc
            if self._tb:
                for l in self._tb:
                    print >>sys.stderr, l,

def run_f(tpool, func, *args, **kw):
    """Run *func* via *tpool*, returning a ``Future`` for the return value or exception.

    :param tpool: a concurrency provider (with a suitable ``.do`` method)
    :param func: a callable
    :param args: variable argument list to pass to *func*
    :param kw: any keyword arguments to pass to *func*
    """
    result = Future()
    tpool.do(result.run, func, *args, **kw)
    return result

class ExceptionList(Exception):
    """A list of exceptions.

    Example::

        try:
            func()
        except ExceptionList, e:
            e.args[0] # is a list of exceptions
    """
    pass

def prun_f(tpool, tasks):
    """Run a set of tasks in parallel.

    Returns a ``Future`` which will resolve either to a list of
    results, the return values of the callables, or to an ``ExceptionList``
    containing all exceptions raised.

    If any exceptions are raised, any normal return values are discarded.

    :param tpool: a concurrency provider (with a suitable ``.do`` method)
    :param tasks: a list of ``(func, args, kw)`` tuples
    """
    result = Future()
    lock = threading.Lock()
    todo = len(tasks)
    results = []
    exceptions = []
    result_list = [None] * todo

    def run_task(i, task):
        func, args, kwargs = task
        exc = None
        try:
            res = func(*args, **kwargs)
        except Exception, exc:
            pass

        with lock:
            if exc is not None:
                exceptions.append(exc)
            else:
                result_list[i] = res
                results.append(res)
            if len(results) + len(exceptions) == todo:
                if exceptions:
                    result.error(ExceptionList(exceptions))
                else:
                    result.resolve(result_list)
    for i, task in enumerate(tasks):
        tpool.do(run_task, i, task)
    if not tasks:
        result.resolve([])
    return result
