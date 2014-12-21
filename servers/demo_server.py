import sys
import Ice
from icecap import idemo


class Printer(idemo.Printer):
    def printString(self, s, curr):
        print s


ic = Ice.initialize(sys.argv)

try:
    adapter = ic.createObjectAdapterWithEndpoints("PrinterAdapter ", "default -p 10000")
    servant = Printer()
    adapter.add(servant, ic.stringToIdentity('printer'))
    adapter.activate()
    ic.waitForShutdown()
finally:
    ic.destroy()
