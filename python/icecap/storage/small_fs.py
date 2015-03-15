import traceback
import simplejson as json
import os
import sys
import shutil
from icecap import istorage
from icecap.base.antenna import Antenna, notifyOnline
from icecap.base.util import openLocal
from icecap.base.rep_log import RepLog
from icecap.storage.data_node import DataNode

class FileShardFactory(object):
    def __init__(self, env):
        self._env = env

    def typeId(self):
        return 'file'

    def makeShard(self, shard):
        return File(self._env, shard)

class FileNode(DataNode, istorage.File):
    """A replicated file store for small files.

    Files are stored under ``<local-data>/file``, with replication data
    under ``<local-data>/file/.rep``.

    :param env: server environment
    """
    def __init__(self, env):
        DataNode.__init__(self, env, FileShardFactory(env))

    def read_async(self, cb, path, curr=None):
        """Get the contents of the specified file as a string.

        :param path: the file to read
        """
        self.master_f(path).call_f('read', path).iceCB(cb)

    def readRep(self, path, curr=None):
        s = self._shardFor(path)
        return self._shard[s].read(path)

    def write_async(self, cb, path, data, curr=None):
        """Set the contents of the specified file.

        :param path: the file to write
        :param data: the data to write
        """
        self.master_f(path).call_f('write', path, data).iceCB(cb)

    def writeRep(self, path, data, curr=None):
        s = self._shardFor(path)
        self._shard[s].write(path, data)

    def list_async(self, cb, shard, curr=None):
        """Returns a list of all files."""
        self.master_f(shard=shard).call_f('list').iceCB(cb)

    def listRep(self, shard, curr=None):
        return self._shard[shard].list()

class File(object):
    def __init__(self, env, shard):
        self._env = env
        self._lpath = 'file/S' + shard
        self._path = os.path.join(env.dataDir(), self._lpath)
        self._log = RepLog(env, self._lpath + '/.rep')

    def _onOnline(self, server_id):
        """Respond to a peer coming online."""
        server, node = server_id.split('-', 1)
        if server != self._env.serverId().split('-', 1)[0]:
            return # nothing to do with us.
        addr = 'file@%s.%sRep' % (server_id, server)
        if self._log.hasSink(addr):
            self._log.update(addr)

    def isNew(self):
        return len(os.listdir(self._path)) < 2

    def peers(self):
        """Returns a list of peers this replica replicates to."""
        return self._log.sinks()

    def addPeer(self, addr, sync):
        """Adds addr as a replica of this one, at the head of the log.

        :param addr: proxy string of the replica to add
        :param sync: (bool) whether to sync data from here to addr
        """
        if sync:
            prx = self._env.getProxy(addr, istorage.FilePrx)
            for path in self._list():
                data = self.read(path)
                prx.update(json.dumps({'path': path, 'data': data}))
        self._log.addSink({'addr': addr, 'method': 'update'})

    def removePeer(self, addr):
        """Removes addr as a replica of this one.

        :param addr: proxy string of the replica to remove
        """
        self._log.removeSink(addr)

    def update(self, info):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        with openLocal(self._env, os.path.join(self._lpath, info['path']), 'w') as out:
            out.write(info['data'])

    def read(self, path):
        assert not path.startswith('.')
        try:
            fh = openLocal(self._env, os.path.join(self._lpath, path))
        except IOError:
            raise istorage.FileNotFound()
        return fh.read()

    def write(self, path, data):
        assert not path.startswith('.')
        with openLocal(self._env, os.path.join(self._lpath, path), 'w') as out:
            out.write(data)
        self._env.do(self._log.append, json.dumps({'path':path, 'data':data}))

    def removeData(self):
        """Removes all data from this replica."""
        shutil.rmtree(self._path)
        self._log = RepLog(self._env, self._lpath + '/.rep')

    def _list(self):
        root = self._path
        plen = len(root) + 1
        for path, dirs, files in os.walk(root):
            if '.rep' in dirs:
                dirs.remove('.rep')
            for f in files:
                yield os.path.join(path, f)[plen:]

    def list(self):
        return list(self._list())

def server(env):
    env.provide('file', 'SmallFSRep', FileNode(env))
    env.provide('antenna', 'SmallFSRep', Antenna(env))
    env.onActivation(notifyOnline, env, env.serverId())
