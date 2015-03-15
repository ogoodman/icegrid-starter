import os
import random
import simplejson as json
from icecap import istorage
from icecap.base.future import Future
from icecap.base.master import mcall_f
from icecap.base.util import getNode, sHash

HI = 2**63-1

def error(exc):
    f = Future()
    f.error(exc)
    return f

class DataNode(object):
    def __init__(self, env, factory):
        self._env = env
        self._factory = factory
        self._type = factory.typeId()
        self._path = os.path.join(env.dataDir(), self._type)
        self._env.onActivation(self._register)
        self._env.subscribe('online', self._onOnline)
        self._mgr = self._env.getProxy(self._type + '@DataManagerGroup', istorage.DataManagerPrx)
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        self._initShards()

    def _initShards(self):
        self._shard = {}
        self._priority = {}
        for d in os.listdir(self._path):
            if d.startswith('S'):
                self.addShard(d[1:])

    def _register(self):
        reg_marker = os.path.join(self._path, '.reg')
        if os.path.exists(reg_marker):
            return
        def done():
            open(reg_marker, 'w').write('')
        name, node = self._env.serverId().split('-', 1)
        addr = '%s@%s-%s.%sRep' % (self._type, name, node, name)
        mcall_f(self._env, self._mgr, 'register', addr).then(done)

    def _shardFor(self, path):
        bits = '{0:08b}'.format(sHash(path))[::-1]
        for s in self._shard:
            if bits.startswith(s):
                return s

    def _getCurrentMaster(self, master_map_s, path, shard):
        master_map = json.loads(master_map_s)
        node = getNode(self._env.serverId())
        for s in self._shard:
            m_pri = 1 if (s in master_map and getNode(master_map[s]) == node) else 0
            self._priority[s][0] = m_pri
        if not self._priority[shard][0]:
            raise istorage.NoShard(path=path)
        return self._shard[shard]

    def master_f(self, path=None, shard=None):
        if shard is None:
            shard = self._shardFor(path)
        if shard not in self._shard:
            return error(istorage.NoShard(path, shard))
        if not self._priority[shard][0]:
            masters_f = mcall_f(self._env, self._mgr, 'getMasters')
            return masters_f.then(self._getCurrentMaster, path, shard)
        return Future(self._shard[shard])

    def addShard(self, shard, curr=None):
        self._shard[shard] = sh = self._factory.makeShard(shard)
        self._priority[shard] = [0, 0 if sh.isNew() else 1, random.randint(0, HI)]

    def removeData(self, shard, curr=None):
        """Remove all data from a shard.

        :param shard: shard to remove data from
        """
        self._shard[shard].removeData()

    def addPeer(self, shard, addr, sync, curr=None):
        """Adds addr as a replica of this one, at the head of the log.

        :param shard: shard for which to add a peer
        :param addr: proxy string of the replica to add
        :param sync: (bool) whether to sync data from here to addr
        """
        self._shard[shard].addPeer(addr, sync)

    def removePeer(self, shard, addr, curr=None):
        """Removes addr as a replica of this one.

        :param shard: shard from which to remove a peer
        :param addr: proxy string of the replica to remove
        """
        self._shard[shard].removePeer(addr)

    def _onOnline(self, server_id):
        for shard in self._shard.values():
            shard._onOnline(server_id)

    def getState(self, curr=None):
        """Returns the replication state of this data replica.

        The state takes the form::

            {'shards': {'': {'replicas': [r0, r1,], 'priority': [p0, p1,]}}}

        """
        shard_state = {}
        for s, sh in self._shard.iteritems():
            shard_state[s] = {'replicas': sh.peers(), 'priority': self._priority[s]}
        return json.dumps({'shards': shard_state})

    def update(self, info_s, curr=None):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        info = json.loads(info_s)
        s = self._shardFor(info['path'])
        self._shard[s].update(info)
