"""Proxy wrapper to handle interaction with DataNodes."""

import Ice
import simplejson as json
from icecap import istorage
from icecap.base.util import sHash, pcall, getAddr

def getState(replicas, register=True):
    """Gets replication state info from a replica group.

    Each replica returns state info in the form::

        {'shards': {s1: {'replicas': [rep11,], 'priority': [p10, p11,]},
                    s2: {'replicas': [rep21,], 'priority': [p20, p21,]}}}

    This function simply gathers the state info from replicas into the form::

        {addr1: state_info1,
         addr2: state_info2, }

    .. note:: register is an implementation detail: when a DataManager uses
        this function it must set *register* False to avoid an infinite recursion.

    :param replicas: a list of replicas to query
    :param register: whether unregistered nodes should register before responding 
    """
    state = {}
    for p, r, e in pcall(replicas, 'getState', register):
        if e is None:
            state[getAddr(p)] = json.loads(r)
    return state

def getShards(state):
    """Converts state into a dictionary of [shard][addr].

    :param state: a dictionary of [addr]['shards'][shard]
    """
    shard_map = {}
    for addr, node in state.iteritems():
        shards = node['shards']
        for s, info in shards.iteritems():
            if s in shard_map:
                shard_map[s][addr] = info
            else:
                shard_map[s] = {addr: info}
    return shard_map

def getMaster(shard_state):
    """Finds the master address for the given shard.

    The shard_state must be a dictionary::

        {addr1: {'priority': [p11, p12,], }, }

    :param shard_state: shard state as returned by getShard
    """
    m_addr = None
    m_priority = []
    for addr, info in shard_state.iteritems():
        if info['priority'] > m_priority:
            m_priority = info['priority']
            m_addr = addr
    return m_addr

# NOTE: currently only file methods are supported. In future different DataNode
# types will require other methods.

class DataClient(object):
    """A DataClient directs calls to the correct replica in a group of DataNodes.

    Example::

        dc = DataClient(e, e.getProxy('file@SmallFSGroup'))
        dc.write('fred', '1')
        dc.read('fred') # -> returns '1'

    :param env: an environment object
    :param group: proxy for a replica group of DataNodes
    """
    def __init__(self, env, group):
        self._env = env
        self._group = group
        self._shards = None
        self._master = {}

    def _getShards(self, refresh=False):
        if self._shards is None or refresh:
            state = getState(self._env.replicas(self._group, refresh))
            self._shards = getShards(state)
            self._master = {}
        return self._shards

    def _findShard(self, path, shard, refresh=False):
        shards = self._getShards(refresh)
        if shard is not None:
            return shard, shards[shard]
        bits = '{0:08b}'.format(sHash(path))[::-1]
        for i in xrange(8):
            s = bits[:i]
            addrs = shards.get(s)
            if addrs is not None:
                return s, addrs
        raise Exception('No shard exists for path "%s"' % path)

    def _findMaster(self, path=None, shard=None, refresh=False):
        s, addrs = self._findShard(path, shard, refresh)
        if s not in self._master:
            addr = getMaster(addrs)
            self._master[s] = self._env.getProxy(addr, self._group)
        return self._master[s]

    def call(self, method, path, *args):
        """Calls ``m.<method>(path, *args)`` where *m* is the master DataNode for *path*.

        :param method: (str) the method to call
        :param path: (str) data item to which the call applies
        :param args: additional arguments
        """
        try:
            m = self._findMaster(path)
            return getattr(m, method)(path, *args)
        except (istorage.NoShard, Ice.NoEndpointException):
            m = self._findMaster(path, refresh=True)
            return getattr(m, method)(path, *args)

    def callByShard(self, method, shard, *args):
        """Calls ``m.<method>(shard, *args)`` where *m* is the master DataNode for *shard*.

        :param method: (str) the method to call
        :param shard: (str) shard to which the call applies
        :param args: additional arguments
        """
        try:
            m = self._findMaster(shard=shard)
            return getattr(m, method)(shard, *args)
        except (istorage.NoShard, Ice.NoEndpointException):
            m = self._findMaster(shard=shard, refresh=True)
            return getattr(m, method)(shard, *args)

    def read(self, path):
        """Calls ``m.read(path)`` on the replica which is master for the shard containing *path*.

        :param path: the file path to read
        """
        return self.call('read', path)

    def write(self, path, data):
        """Calls ``m.write(path, data)`` on the replica which is master for the shard containing *path*.

        :param path: the file path to write
        :param data: the data to write
        """
        return self.call('write', path, data)

    def list(self, shard):
        """Lists all files in the specified shard.

        :param shard: the shard to list
        """
        return self.callByShard('list', shard)

    def remove(self, path):
        """Removes the specified file.

        :param path: the file to remove
        """
        return self.call('remove', path)
