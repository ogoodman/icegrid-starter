from icecap.base.env import Env

env = Env()

printer = env.get_proxy('printer@PrinterGroup')

n = 42
nn = printer.addOne(n)
print '%s + 1 = %s' % (n, nn)

