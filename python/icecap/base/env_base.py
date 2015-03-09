from icecap.base.future import Future
from icecap.base.publisher import Publisher

class EnvBase(Publisher):
    """Environment services common to Env and FakeEnv."""

    def __init__(self):
        Publisher.__init__(self)
        self._activation_callbacks = []

    def _runActivationCallbacks(self):
        """Runs all callbacks added by onActivation."""
        for func, args in self._activation_callbacks:
            func(*args)
        self._activation_callbacks = []

    def do_f(self, func, *args):
        """Runs ``func(*args)`` in the work queue.

        The work queue is a single thread. The result is returned as a Future.

        :param func: a function to call
        :param args: arguments for *func*
        """
        f = Future()
        self.do(f.run, func, *args)
        return f

    def onActivation(self, func, *args):
        """Add a callback function to be run once this server is activated.

        :param func: a function
        :param args: optional arguments to supply when calling *func*
        """
        self._activation_callbacks.append((func, args))

