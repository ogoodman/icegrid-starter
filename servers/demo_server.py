from icecap import idemo
from icecap.base.env import Env

class Printer(idemo.Printer):
    def printString(self, s, curr):
        print s
    def addOne(self, n, curr):
        return n + 1

env = Env()
ic = env.get_communicator()

adapter = ic.createObjectAdapter("PrinterAdapter")
servant = Printer()
adapter.add(servant, ic.stringToIdentity('printer'))
adapter.activate()
ic.waitForShutdown()
