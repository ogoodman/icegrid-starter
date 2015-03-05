"""Proxy wrapper to handle interaction with DataNodes."""

import simplejson as json
from icecap.base.util import sHash, pcall, getAddr

def getState(replicas):
    """Gets replication state info from a replica group.

    Each replica returns state info in the form::

        {'shards': {s1: {'replicas': [rep11,], 'priority': [p10, p11,]},
                    s2: {'replicas': [rep21,], 'priority': [p20, p21,]}}}

    This function simply gathers the state info from replicas into the form::

        {addr1: state_info1,
         addr2: state_info2, }

    :param replicas: a list of replicas to query
    """
    state = {}
    for p, r, e in pcall(replicas, 'getState'):
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

class DataClient(object):
    def __init__(self, env, group):
        self._env = env
        self._group = group
        self._shards = None
        self._master = {}

    def _getShards(self, refresh=False):
        if self._shards is None or refresh:
            self._shards = getShards(getState(self._env.replicas(self._group, refresh)))
            self._master = {}
        return self._shards

    def _findShard(self, path):
        shards = self._getShards()
        bits = '{0:08b}'.format(sHash(path))[::-1]
        for i in xrange(8):
            s = bits[:i]
            addrs = shards.get(s)
            if addrs is not None:
                return s, addrs
        raise Exception('No shard exists for path "%s"' % path)

    def _findMaster(self, path):
        s, addrs = self._findShard(path)
        if s not in self._master:
            addr = getMaster(addrs)
            self._master[s] = self._env.getProxy(addr, self._group)
        return self._master[s]

    def read(self, path):
        m = self._findMaster(path)
        return m.read(path)

    def write(self, path, data):
        m = self._findMaster(path)
        m.write(path, data)

