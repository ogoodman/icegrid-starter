from icecap.base.env import Env
from icecap.base.util import pcall

env = Env()

printer = env.get_proxy('printer@PrinterGroup')

printer.printString('Hello!')

n = 42
nn = printer.addOne(n)
print '%s + 1 = %s' % (n, nn)

print pcall(env.replicas(printer), 'masterPriority')
print printer.info()

