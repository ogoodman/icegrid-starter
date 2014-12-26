import random
from icecap import idemo

LO, HI = -2**31, 2**31-1

class Printer(idemo.Printer):
    def printString(self, s, curr=None):
        print s
    def addOne(self, n, curr=None):
        return n + 1
    def getRand(self, curr=None):
        return random.randint(LO, HI)

def setup(env):
    random.seed()
    env.provide('printer', 'Printer', Printer())
    env.provide('printer', 'PrinterRep', Printer())
