import os
from icecap import istorage
from icecap.base.antenna import Antenna, notifyOnline
from icecap.base.util import openLocal
from icecap.storage.data_node import DataNode
from icecap.storage.data_shard import DataShard

class FileShardFactory(object):
    def __init__(self, env):
        self._env = env

    def typeId(self):
        return 'file'

    def makeShard(self, shard):
        return FileShard(self._env, 'file/S' + shard)

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

    def remove_async(self, cb, path, curr=None):
        self.master_f(path).call_f('remove', path).iceCB(cb)

    def removeRep(self, path):
        s = self._shardFor(path)
        self._shard[s].remove(path)

class FileShard(DataShard):
    def update(self, info):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        data = info['data']
        if data is None:
            try:
                os.unlink(os.path.join(self._path, info['path']))
            except OSError:
                pass
        else:
            with openLocal(self._env, os.path.join(self._lpath, info['path']), 'w') as out:
                out.write(info['data'])

    def dump(self, path):
        assert not path.startswith('.')
        try:
            data = openLocal(self._env, os.path.join(self._lpath, path)).read()
        except IOError:
            d = []
        else:
            d = [repr({'path': path, 'data': data}),]
        return self._log.end(), iter(d)

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
        self._env.do(self.append, repr({'path':path, 'data':data}))

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

    def remove(self, path):
        assert not path.startswith('.')
        try:
            os.unlink(os.path.join(self._path, path))
            self._env.do(self.append, repr({'path':path, 'data':None}))
        except OSError:
            pass

def server(env):
    env.provide('file', 'SmallFSRep', FileNode(env))
    env.provide('antenna', 'SmallFSRep', Antenna(env))
    env.onActivation(notifyOnline, env, env.serverId())
