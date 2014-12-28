import sys
import random
from icecap import idemo
from icecap.base.master import MasterInfo

LO, HI = -2**31, 2**31-1

class Printer(idemo.Printer):
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
        self._env = env
        self._master_info = None

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

    def masterPriority(self, curr=None):
        """Returns the pair (*is_master, priority*) of type (``bool``, ``int64``).

        This must be implemented by servants in a replica group where one of the
        replicas will be elected master and the rest slaves. 

        The rule is that if one of the servants returns ``True`` for
        *is_master*, that one is the master. If none return ``True``
        the servant which returned the highest *priority* is master
        (and will start returning ``True`` for *is_master* as soon as
        it accepts the next call for which it must be master).
        """
        if self._master_info is None:
            self._master_info = MasterInfo(self._env, self._proxy)
        return self._master_info.masterPriority()

    def info(self, curr=None):
        """Debug method: currently returns the proxy string of the master."""
        if self._master_info is None:
            self._master_info = MasterInfo(self._env, self._proxy)
        return repr(self._master_info.findMaster())


def setup(env):
    """Sets up the demo ``Printer`` server by adding ``Printer`` servants to the
    ``Printer`` and ``PrinterRep`` adapters.

    :param env: an environment resource factory
    """
    random.seed()
    env.provide('printer', 'Printer', Printer(env))
    env.provide('printer', 'PrinterRep', Printer(env))
