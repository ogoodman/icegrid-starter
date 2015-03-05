import sys
from icecap import istorage
from icecap.base.master import MasterOrSlave
from icecap.storage.data_client import getState, getMaster

def getShard(state, shard):
    """Extracts the state of a particular shard.

    State info for the specified shard is returned in the form::

        {addr1: {'replicas': [r11, r12,], 'priority': [p11, p12,]}, }

    :param state: state info in the form returned by getState
    :param shard: the shard to extract
    """
    nodes = {}
    for addr, node in state.iteritems():
        info = node['shards'].get(shard)
        if info is not None:
            nodes[addr] = info
    return nodes

class DataManager(istorage.DataManager, MasterOrSlave):
    def __init__(self, env, group):
        MasterOrSlave.__init__(self, env)
        self._group = group

    def register_async(self, cb, addr, curr=None):
        self.assertMaster_f().then(self._env.do_f, self.addReplica, '', addr).iceCB(cb)

    def remove_async(self, cb, addr, curr=None):
        self.assertMaster_f().then(self._env.do_f, self.removeReplica, '', addr).iceCB(cb)

    def addReplica(self, shard, addr):
        """Adds a new replica to the group.

        Adds bi-directional links between the new replica at *prx* and all
        existing replicas and populates the new replica with all existing data.

        :param shard: the shard to remove addr from
        :param addr: the replica to be removed
        """
        replicas = self._env.replicas(self._group, refresh=True)
        state = getState(replicas)
        assert addr in state

        shard_state = getShard(state, '')
        m_addr = getMaster(shard_state)

        if m_addr is None:
            # When the first replica registers it need not have any shards
            return

        env = self._env
        prx = env.getProxy(addr, self._group)
        for a, s in shard_state.iteritems():
            if a == addr:
                continue
            p = env.getProxy(a, self._group)
            p.addPeer(shard, addr, a == m_addr)
            prx.addPeer(shard, a, False)

    def removeReplica(self, shard, addr):
        """Removes a replica from the group.

        Removes data from the replica and then removes all links between the
        replica and the rest of the group.

        :param shard: the shard to remove addr from
        :param addr: the replica to be removed
        """
        replicas = self._env.replicas(self._group, refresh=True)
        state = getState(replicas)
        shard_state = getShard(state, '')
        if addr not in shard_state:
            return

        m_addr = getMaster(shard_state)
        assert addr != m_addr

        env = self._env
        prx = env.getProxy(addr, self._group)
        prx.removeData(shard)
        for a, s in shard_state.iteritems():
            if a == addr:
                continue
            p = env.getProxy(a, self._group)
            p.removePeer(shard, addr)
            prx.removePeer(shard, a)

def server(env):
    small_fs = env.getProxy('file@SmallFSGroup', istorage.FilePrx)
    env.provide('file', 'DataManagerRep', DataManager(env, small_fs))
