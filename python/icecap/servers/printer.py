from icecap import idemo

class Printer(idemo.Printer):
    def printString(self, s, curr=None):
        print s
    def addOne(self, n, curr=None):
        return n + 1

def setup(env):
    env.provide('printer', 'Printer', Printer())
    env.provide('printer', 'PrinterRep', Printer())
