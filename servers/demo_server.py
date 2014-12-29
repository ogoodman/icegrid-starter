import atexit
import sys
import Ice
from iceapp.printer import Printer

ic = Ice.initialize(sys.argv)
atexit.register(ic.destroy)

adapter = ic.createObjectAdapter('Printer')
servant = Printer()
adapter.add(servant, ic.stringToIdentity('printer'))
adapter.activate()

ic.waitForShutdown()
