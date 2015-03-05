import simplejson as json
import os
import sys
import shutil
from icecap import istorage
from icecap.base.antenna import Antenna, notifyOnline
from icecap.base.master import findLocal, MasterOrSlave, mcall_f
from icecap.base.util import openLocal, getAddr, getServer
from icecap.base.rep_log import RepLog

class File(istorage.File, MasterOrSlave):
    """A replicated file store for small files.

    Files are stored under ``<local-data>/files``, with replication data
    under ``<local-data>/files/.rep``.

    :param env: server environment
    """
    def __init__(self, env):
        MasterOrSlave.__init__(self, env)
        self._log = RepLog(env, 'files/.rep')
        self._path = os.path.join(env.dataDir(), 'files')
        self._new_replica = len(os.listdir(self._path)) < 2
        self._env.onActivation(self._register)
        self._env.subscribe('online', self._onOnline)

    def _register(self):
        reg_marker = os.path.join(self._path, '.rep/registered')
        if os.path.exists(reg_marker):
            return
        def done():
            open(reg_marker, 'w').write('')
        name, node = self._env.serverId().split('-', 1)
        addr = 'file@%s-%s.%sRep' % (name, node, name)
        mgr = self._env.getProxy('file@DataManagerGroup', istorage.DataManagerPrx)
        mcall_f(self._env, mgr, 'register', addr).then(done)

    def addPeer(self, shard, addr, sync, curr=None):
        """Adds addr as a replica of this one, at the head of the log.

        :param shard: not used (SmallFS has only one shard)
        :param addr: proxy string of the replica to add
        :param sync: (bool) whether to sync data from here to addr
        """
        if sync:
            prx = self._env.getProxy(addr, self._proxy)
            for path in self._list():
                data = self.readRep(path)
                prx.update(json.dumps({'path': path, 'data': data}))
        self._log.addSink({'addr': addr, 'method': 'update'})

    def removePeer(self, shard, addr, curr=None):
        """Removes addr as a replica of this one.

        :param shard: not used (SmallFS has only one shard)
        :param addr: proxy string of the replica to remove
        """
        self._log.removeSink(addr)

    def peers(self, curr=None):
        """Returns a list of peers this replica replicates to."""
        return self._log.sinks()

    def removeData(self, shard, curr=None):
        """Removes all data from this replica."""
        assert not self._is_master
        assert shard == ''
        shutil.rmtree(self._path)
        self._log = RepLog(self._env, 'files/.rep')
        self._new_replica = True

    def _onOnline(self, server_id):
        """Respond to a peer coming online."""
        server, node = server_id.split('-', 1)
        if server != self._env.serverId().split('-', 1)[0]:
            return # nothing to do with us.
        addr = 'file@%s.%sRep' % (server_id, server)
        if self._log.hasSink(addr):
            self._log.update(addr)

    def masterState(self, curr=None):
        """Returns a list of *int64* giving the master priority of this replica.

        The first entry is 1 if this replica is master, 0 otherwise. The
        second entry gives priority to replicas that have already been
        used. The last entry is a random number to use as a tie-breaker.
        """
        m_count = 1 if self._is_master else 0
        return [m_count, 0 if self._new_replica else 1, self._master_priority]

    def getState(self, curr=None):
        """Returns the replication state of this data replica.

        The state takes the form::

            {'shards': {'': {'replicas': [r0, r1,], 'priority': [p0, p1,]}}}

        at least in the case of a SmallFS replica which only ever has the ``''`` shard.
        """
        shard = {'replicas': self.peers(), 'priority': self.masterState()}
        return json.dumps({'shards': {'': shard}})

    def read_async(self, cb, path, curr=None):
        """Get the contents of the specified file as a string.

        :param path: the file to read
        """
        self.assertMaster_f().then(self.readRep, path).iceCB(cb)

    def readRep(self, path, curr=None):
        assert not path.startswith('.')
        try:
            fh = openLocal(self._env, os.path.join('files', path))
        except IOError:
            raise istorage.FileNotFound()
        return fh.read()

    def write_async(self, cb, path, data, curr=None):
        """Set the contents of the specified file.

        :param path: the file to write
        :param data: the data to write
        """
        self.assertMaster_f().then(self.writeRep, path, data).iceCB(cb)

    def writeRep(self, path, data, curr=None):
        assert not path.startswith('.')
        with openLocal(self._env, os.path.join('files', path), 'w') as out:
            out.write(data)
        self._env.do(self._log.append, json.dumps({'path':path, 'data':data}))

    def update(self, info_s, curr=None):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        info = json.loads(info_s)
        with openLocal(self._env, os.path.join('files', info['path']), 'w') as out:
            out.write(info['data'])

    def _list(self):
        root = os.path.join(self._env.dataDir(), 'files')
        plen = len(root) + 1
        for path, dirs, files in os.walk(root):
            if '.rep' in dirs:
                dirs.remove('.rep')
            for f in files:
                yield os.path.join(path, f)[plen:]

    def list_async(self, cb, curr=None):
        """Returns a list of all files."""
        self.assertMaster_f().then(self.listRep).iceCB(cb)

    def listRep(self, curr=None):
        return list(self._list())

def server(env):
    env.provide('file', 'SmallFSRep', File(env))
    env.provide('antenna', 'SmallFSRep', Antenna(env))
    env.onActivation(notifyOnline, env, env.serverId())
