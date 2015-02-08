import sys
import IceGrid
from icecap import ibase

class Antenna(ibase.Antenna):
    """A servant for monitoring and communicating server environment state.

    :param env: an environment
    """
    def __init__(self, env):
        self._env = env

    def serverOnline(self, server_id, curr=None):
        """Called when a server goes online so the local environment can publish an 'online' event.

        :param server_id: the id of the server just started
        """
        self._env.notify('online', server_id)

def notifyOnline(env, server_id):
    """Broadcasts a serverOnline call to all currently active servers.

    :param env: an environment
    :param server_id: the id of the server going online
    """
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
