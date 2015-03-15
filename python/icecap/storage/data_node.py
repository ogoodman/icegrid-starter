from ast import literal_eval
import os
import random
import shutil
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
    """A DataNode provides operations common to all replicated sharded data types.
    Its main function is to manage a persistent collection of shards.

    The shard factory argument expects an object with methods:

    * ``typeId()`` returning a short name for the data type, and
    * ``makeShard(shard)`` for instantiating shard objects.

    Shard objects are assumed to store their data under
    ``env.dataDir() + '/' + factory.typeId() + '/S' + shard``.
    They must implement the interface provided by a DataShard.

    DataNodes interact with a data manager at ``<factory.typeId()>@DataManagerGroup``.

    :param env: an environment object
    :param factory: a shard factory
    """
    def __init__(self, env, factory):
        self._env = env
        self._factory = factory
        self._type = factory.typeId()
        self._path = os.path.join(env.dataDir(), self._type)
        self._env.subscribe('online', self._onOnline)
        self._mgr = self._env.getProxy(self._type + '@DataManagerGroup', istorage.DataManagerPrx)
        self._initShards()

    def _initShards(self):
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        self._shard = {}
        self._priority = {}
        for d in os.listdir(self._path):
            if d.startswith('S'):
                self.addShard(d[1:])

    def register_f(self):
        """Register with the data manager."""
        reg_marker = os.path.join(self._path, '.reg')
        if os.path.exists(reg_marker):
            return Future(None)
        def done():
            open(reg_marker, 'w').write('')
        name, node = self._env.serverId().split('-', 1)
        addr = '%s@%s-%s.%sRep' % (self._type, name, node, name)
        return mcall_f(self._env, self._mgr, 'register', addr).then(done)

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
        """Get the shard for the given *path* or *shard*. If the shard is not the master
        an ``istorage.NoShard`` exception is raised.
        
        One or other of *path* or *shard* should be specified.

        :param path: path to find the shard for
        :param shard: the shard to find
        """
        if shard is None:
            shard = self._shardFor(path)
        if shard not in self._shard:
            return error(istorage.NoShard(path, shard))
        if not self._priority[shard][0]:
            masters_f = mcall_f(self._env, self._mgr, 'getMasters')
            return masters_f.then(self._getCurrentMaster, path, shard)
        return Future(self._shard[shard])

    def addShard(self, shard, curr=None):
        """Add a new persistent shard.

        :param shard: the shard to add
        """
        self._shard[shard] = sh = self._factory.makeShard(shard)
        self._priority[shard] = [0, 0 if sh.isNew() else 1, random.randint(0, HI)]

    def reset(self, curr=None):
        """Removes all data on this node including registration."""
        shutil.rmtree(self._path)
        self._initShards()

    def removeData(self, shard, curr=None):
        """Remove all data from a shard.

        :param shard: shard to remove data from
        """
        self._shard[shard].removeData()
        del self._shard[shard]

    def addPeer(self, shard, addr, sync, curr=None):
        """Tells the specified shard to push replication data to a DataNode at *addr*.

        :param shard: shard for which to add a peer
        :param addr: proxy string of the replica to add
        :param sync: (bool) whether to sync data from here to addr
        """
        self._shard[shard].addPeer(addr, sync)

    def removePeer(self, shard, addr, curr=None):
        """Tells the specified shard to stop pushing replication data to the DataNode at *addr*.

        :param shard: shard from which to remove a peer
        :param addr: proxy string of the replica to remove
        """
        self._shard[shard].removePeer(addr)

    def _onOnline(self, server_id):
        server, node = server_id.split('-', 1)
        if server != self._env.serverId().split('-', 1)[0]:
            return # nothing to do with us.
        addr = '%s@%s.%sRep' % (self._type, server_id, server)
        for shard in self._shard.values():
            shard._onOnline(addr)

    def getState_async(self, cb, register, curr=None):
        """Returns the replication state of this data replica.

        The state takes the form::

            {'shards': {'': {'replicas': [r0, r1,], 'priority': [p0, p1,]}}}

        :param register: whether to register first if this node is unregistered
        """
        reg = self.register_f() if register else Future(None)
        reg.then(self._getState).iceCB(cb)

    def _getState(self):
        shard_state = {}
        for s, sh in self._shard.iteritems():
            shard_state[s] = {'replicas': sh.peers(), 'priority': self._priority[s]}
        return json.dumps({'shards': shard_state})

    def update(self, info_s, curr=None):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        info = literal_eval(info_s)
        s = self._shardFor(info['path'])
        self._shard[s].update(info)
