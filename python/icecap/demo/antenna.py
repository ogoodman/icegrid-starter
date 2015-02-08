import sys
import IceGrid
from icecap import ibase

class Antenna(ibase.Antenna):
    def __init__(self, env):
        self._env = env

    def serverOnline(self, server_id, curr=None):
        print 'Online:', server_id
        sys.stdout.flush()

def notifyOnline(env, server_id):
    grid = env.grid()
    antenna_adapter = {}
    for a_id in grid.getAllAdapterIds():
        if not '.' in a_id:
            continue
        s_id, adapter = a_id.split('.', 1)
        if s_id == server_id:
            continue
        if (s_id not in antenna_adapter) or adapter.endswith('Rep'):
            antenna_adapter[s_id] = a_id
    for s_id, a_id in antenna_adapter.iteritems():
        if grid.serverIsActive(s_id):
            prx = env.getProxy('antenna@%s' % a_id, ibase.AntennaPrx, one_way=True)
            prx.serverOnline(server_id)
