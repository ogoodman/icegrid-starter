import atexit
import sys
import Ice
from icecap import config

class Env(object):
    def __init__(self):
        self._ic = None

    def get_communicator(self):
        """Returns the Ice.Communicator for the configured grid."""
        if self._ic is None:
            self._ic = Ice.initialize(sys.argv)
            atexit.register(self._ic.destroy)

            reg_proxy = self._ic.stringToProxy("IceGrid/Locator:tcp -h %s -p 4061" % config.ICE_REG_HOST)
            registry = Ice.LocatorPrx.uncheckedCast(reg_proxy)
            self._ic.setDefaultLocator(registry)
        return self._ic
