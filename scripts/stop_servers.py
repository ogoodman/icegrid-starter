#!/usr/bin/python

from icecap.base.env import Env

e = Env()
g = e.grid()

for server_id in g.getAllServerIds():
    g.stopServer(server_id)
