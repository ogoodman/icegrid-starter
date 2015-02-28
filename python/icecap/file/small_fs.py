import json
import os
import sys
from icecap import idemo
from icecap.base.antenna import Antenna, notifyOnline
from icecap.base.master import findLocal, MasterOrSlave
from icecap.base.util import openLocal, getAddr, getServer
from icecap.base.rep_log import RepLog

class File(idemo.File, MasterOrSlave):
    """A replicated file store for small files.

    Files are stored under ``<local-data>/files``, with replication data
    under ``<local-data>/files/.rep``.

    .. note:: Work in progress. 

    :param env: server environment
    """
    def __init__(self, env):
        MasterOrSlave.__init__(self, env)
        self._log = RepLog(env, 'files/.rep')
        self._path = os.path.join(env.dataDir(), 'files')
        self._new_replica = len(os.listdir(self._path)) < 2
        self._peers_added = False
        env.subscribe('online', self._onOnline)

    def _addPeers(self):
        if not self._peers_added:
            for p in findLocal(self._env, self._proxy)[1]:
                self._addPeer(p)
            self._peers_added = True

    def _addPeer(self, prx):
        if self._log.hasSink(getAddr(prx)):
            return
        self.isMaster_f().then(lambda is_m: is_m and self._addNewPeer(prx))

    def _addNewPeer(self, prx):
        """Adds a new replica to the group.

        This must run only on the master. It adds bi-directional links between
        the new replica at *prx* and all existing replicas and populates
        the new replica with all existing file.

        :param prx: proxy or proxy string for the new replica
        """
        addr = getAddr(prx)
        if isinstance(prx, basestring):
            prx = self._env.getProxy(addr, self._proxy)
        for a in self._log.sinks():
            p = self._env.getProxy(a, self._proxy)
            p.addPeer(addr)
            prx.addPeer(a)
        for path in self._list():
            data = self.readRep(path)
            prx.update(json.dumps({'path': path, 'data': data}))
        self.addPeer(addr)
        prx.addPeer(getAddr(findLocal(self._env, self._proxy)[0]))

    def addPeer(self, addr, curr=None):
        """Adds addr as a replica of this one, at the head of the log.

        :param addr: proxy string of the replica to add
        """
        self._log.addSink({'addr': addr, 'method': 'update'})

    def _onOnline(self, server_id):
        """Respond to a peer coming online."""
        server, node = server_id.split('-', 1)
        if server != self._env.serverId().split('-', 1)[0]:
            return # nothing to do with us.
        addr = 'file@%s.%sRep' % (server_id, server)
        if not self._log.hasSink(addr):
            self._addPeer(addr)
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
            raise idemo.FileNotFound()
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
        self._addPeers()
        self._log.append(json.dumps({'path':path, 'data':data}))

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
