import atexit
import sys
import Ice
import icegrid_config
from iceapp import idemo

ic = Ice.initialize(sys.argv)
atexit.register(ic.destroy)

reg_proxy = ic.stringToProxy('IceGrid/Locator:tcp -h %s -p 4061' % icegrid_config.ICE_REG_HOST)
registry = Ice.LocatorPrx.uncheckedCast(reg_proxy)
ic.setDefaultLocator(registry)


printer = idemo.PrinterPrx.uncheckedCast(ic.stringToProxy('printer@Printer-node1.Printer'))

printer.printString('Hello!')

n = 42
nn = printer.addOne(n)
print '%s + 1 = %s' % (n, nn)

