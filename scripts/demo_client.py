#!/usr/bin/python

import json
from icecap.base.env import Env
from icecap.base.util import pcall
from icecap.base.master import mcall

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
