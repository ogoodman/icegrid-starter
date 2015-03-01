import sys
from icecap import istorage
from icecap.base.master import MasterOrSlave, mcall
from icecap.base.util import call_f, getAddr

def addReplica(env, fs, addr):
    """Adds a new replica to the group.

    Adds bi-directional links between the new replica at *prx* and all
    existing replicas and populates the new replica with all existing data.
    """
    sinks = mcall(env, fs, 'peers')
    m_addr = getAddr(fs._master)
    sinks.append(m_addr)
    if addr in sinks:
        return
    prx = env.getProxy(addr, fs)
    for a in sinks:
        p = env.getProxy(a, fs)
        p.addPeer(addr, a == m_addr)
        prx.addPeer(a, False)

def removeReplica(env, fs, addr):
    """Removes a replica from the group.

    Removes data from the replica and then removes all links between the
    replica and the rest of the group.
    """
    sinks = mcall(env, fs, 'peers')
    m_addr = getAddr(fs._master)
    sinks.append(m_addr)
    assert addr != m_addr
    if addr not in sinks:
        return
    prx = env.getProxy(addr, fs)
    prx.removeData()
    sinks.remove(addr)
    for a in sinks:
        p = env.getProxy(a, fs)
        p.removePeer(addr)
        prx.removePeer(a)

class DataManager(istorage.DataManager, MasterOrSlave):
    def __init__(self, env):
        MasterOrSlave.__init__(self, env)
        self._small_fs = env.getProxy('file@SmallFSGroup', istorage.FilePrx)

    def register_async(self, cb, addr, curr=None):
        self.assertMaster_f().then(self._env.do_f, self._register, addr).iceCB(cb)

    def remove_async(self, cb, addr, curr=None):
        self.assertMaster_f().then(self._env.do_f, self._remove, addr).iceCB(cb)

    def _register(self, addr):
        addReplica(self._env, self._small_fs, addr)

    def _remove(self, addr):
        removeReplica(self._env, self._small_fs, addr)

def server(env):
    env.provide('file', 'DataManagerRep', DataManager(env))
