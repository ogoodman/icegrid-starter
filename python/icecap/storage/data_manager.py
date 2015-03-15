import simplejson as json
import sys
from icecap import istorage
from icecap.base.master import MasterOrSlave
from icecap.storage.data_client import getState, getMaster, getShards

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
    """Handles operations on DataNodes that are difficult to decentralise.

    :param env: an environment object
    :param group: replica group proxy for the DataNodes to be managed
    """
    def __init__(self, env, group):
        MasterOrSlave.__init__(self, env)
        self._group = group

    def register_async(self, cb, addr, curr=None):
        """Called when a DataNode goes online for the first time ever."""
        self.assertMaster_f().then(self._env.do_f, self.registerNode, addr).iceCB(cb)

    def remove_async(self, cb, addr, curr=None):
        """Removes a DataNode permanently."""
        self.assertMaster_f().then(self._env.do_f, self.removeReplica, '', addr).iceCB(cb)

    def getMasters_async(self, cb, curr=None):
        self.assertMaster_f().then(self._env.do_f, self.getMasters).iceCB(cb)

    def getMasters(self):
        replicas = self._env.replicas(self._group, refresh=True)
        state = getState(replicas)
        shard_map = getShards(state)
        master_map = {}
        for s, shard_state in shard_map.iteritems():
            master_map[s] = getMaster(shard_state)
        return json.dumps(master_map)

    def registerNode(self, addr):
        """Registers a new DataNode.

        Currently this just adds a single catch-all shard to each new node.
        Eventually it will only add a shard if there is a need. Re-balancing
        operations will take care of populating available nodes which have
        no shard initially.

        :param addr: the address of the new node
        """
        replicas = self._env.replicas(self._group, refresh=True)
        state = getState(replicas)

        prx = self._env.getProxy(addr, self._group)

        if len(state[addr]['shards']) == 0:
            prx.addShard('')
            self.addReplica('', addr)

    def addReplica(self, shard, addr):
        """Adds a new replica to the group.

        Adds bi-directional links between the new replica at *addr* and all
        existing replicas and populates the new replica with all existing data.

        :param shard: the shard to be added
        :param addr: the replica to be added
        """
        replicas = self._env.replicas(self._group, refresh=True)
        state = getState(replicas)

        shard_state = getShard(state, shard)
        m_addr = getMaster(shard_state)

        assert m_addr is not None

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
