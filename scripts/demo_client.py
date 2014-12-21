import sys
import Ice
from icecap import idemo

ic = Ice.initialize(sys.argv)

try:
    printer = idemo.PrinterPrx.uncheckedCast(ic.stringToProxy("printer:default -p 10000"))
    printer.printString("Hello World!")
finally:
    ic.destroy()
