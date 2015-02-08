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

    def onActivation(self, func, *args):
        """Add a callback function to be run once this server is activated.

        :param func: a function
        :param args: optional arguments to supply when calling *func*
        """
        self._activation_callbacks.append((func, args))

