import sys
import random
from icecap import idemo
from icecap.base.master import MasterOrSlave

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

        p_prx = env.get_proxy('printer@PrinterGroup')
        p_prx.getRand()      # get a random number from the server

    :param env: an environment resource factory
    """
    def __init__(self, env):
        MasterOrSlave.__init__(self, env)

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

    def masterNode(self, curr=None):
        """Returns the master node."""
        self.assertMaster()
        return self._env.server_id().rsplit('-', 1)[-1]

    def serverId(self, curr=None):
        """Returns the server-id."""
        return self._env.server_id()
