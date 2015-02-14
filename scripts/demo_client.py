#!/usr/bin/python

import json
from icecap.base.env import Env
from icecap.base.util import pcall, fcall, pcall_f
from icecap.base.master import mcall, findMaster_f

env = Env()

printer = env.getProxy('printer@DemoGroup')

printer.printString('Hello!')

n = 42
nn = printer.addOne(n)
print '%s + 1 = %s' % (n, nn)

print pcall(env.replicas(printer), 'masterState')
print mcall(env, printer, 'masterNode')

ev = env.getProxy('events@Demo-node1.Demo')
sink_info = {'addr': 'printer@Demo-node2.Demo', 'method':'printString'}
ev.follow('foo', json.dumps(sink_info))

ev.send('foo', 'Garply')

print '5! = ', printer.fact(5)

mstate = pcall_f(env.replicas(printer), 'masterState')

def negate(n, b):
    return -n + b

number = fcall(printer, 'addOne', 1).then(negate, -1)
master = findMaster_f(env.replicas(printer))

for r in mstate.wait():
    print r

print 'number =', number.wait()

print 'master =', master.wait()
