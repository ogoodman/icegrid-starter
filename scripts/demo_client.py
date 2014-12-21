from icecap import idemo
from icecap.base.env import Env

env = Env()

ic = env.get_communicator()

printer = idemo.PrinterPrx.uncheckedCast(ic.stringToProxy("printer@PrinterAdapter"))
printer.printString("Hello World!")
