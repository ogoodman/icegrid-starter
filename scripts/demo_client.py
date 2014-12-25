from icecap import idemo
from icecap.base.env import Env

env = Env()

ic = env.get_communicator()

addr = "printer@PrinterGroup"
printer = idemo.PrinterPrx.uncheckedCast(ic.stringToProxy(addr))
n = 42
nn = printer.addOne(n)
print '%s + 1 = %s' % (n, nn)

