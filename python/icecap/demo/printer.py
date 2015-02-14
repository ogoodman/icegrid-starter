import sys
import random
from icecap import idemo
from icecap.base.master import MasterOrSlave, findLocal
from icecap.base.future import Future
from icecap.base.util import call_f

LO, HI = -2**31, 2**31-1

random.seed()

class Printer(MasterOrSlave, idemo.Printer):
    """A simple servant, given for demonstration purposes.

    Usage::

        p = Printer(env)

        p.printString('Hi!') # prints 'Hi!\\n' to standard output
        p.addOne(1)          # returns 2
        p.getRand()          # returns an unpredictable number

    .. note:: being a *servant* means this object is normally accessed
              remotely.

    Example::

        p_prx = env.getProxy('printer@PrinterGroup')
        p_prx.getRand()      # get a random number from the server

    :param env: an environment resource factory
    """
    def __init__(self, env):
        MasterOrSlave.__init__(self, env)
        self._peer = None

    def printString(self, s, curr=None):
        """Print *s* to standard output.

        .. note:: You should be able to see this using the 'Retrieve stdout'
                  *node context-menu item* in the IceGridGUI tool.

        :param s: the string to print
        """
        print s
        sys.stdout.flush()

    def addOne(self, n, curr=None):
        """Adds one to *n* and returns it.

        :param n: the number to add one to
        """
        return n + 1

    def getRand(self, curr=None):
        """Returns a random 32-bit integer."""
        return random.randint(LO, HI)

    def masterNode_f(self):
        return self.assertMaster_f().then(self._masterNode)

    def _masterNode(self, _=None):
        return self._env.serverId().rsplit('-', 1)[-1]

    def masterNode_async(self, cb, curr=None):
        # Boilerplate resolving via Future.
        self.masterNode_f().callback(cb.ice_response, cb.ice_exception)

    def serverId(self, curr=None):
        """Returns the server-id."""
        return self._env.serverId()

    def peer(self):
        if self._peer is None:
            self._peer = findLocal(self._env, self._proxy)[1][0]
        return self._peer

    def fact(self, n, curr=None):
        """The usual factorial function (Ice int result overflows at n=13).

        This recursively calls other servants in the replica group.
        """
        # This will use up 1 thread per recursion level and very
        # quickly cause a deadlock.
        if n <= 1:
            return 1
        return n * self.peer().fact(n-1)

    def fact_f(self, n):
        # This returns a future instead of a number but looks
        # similar to the synchronous version.
        if n <= 1:
            return Future(1)
        f = call_f(self.peer(), 'fact', n-1)
        return f.then(lambda n0: n * n0)

    def fact_async(self, cb, n, curr=None):
        # This is boilerplate, adapting Ice async to Future.
        self.fact_f(n).callback(cb.ice_response, cb.ice_exception)
