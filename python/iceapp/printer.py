import sys
import random
from iceapp import idemo

LO, HI = -2**31, 2**31-1

class Printer(idemo.Printer):
    """A simple servant, given for demonstration purposes.

    Usage::

        p = Printer()

        p.printString('Hi!') # prints 'Hi!\\n' to standard output
        p.addOne(1)          # returns 2
        p.getRand()          # returns an unpredictable number

    .. note:: being a *servant* means this object is normally accessed
              remotely.

    Example::

        p_prx = idemo.PrinterPrx.uncheckedCast(ic.stringToProxy('printer@Printer-node1.Printer'))
        p_prx.getRand()      # get a random number from the server
    """

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
