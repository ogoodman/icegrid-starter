import json
import os
from icecap import idemo
from icecap.base.master import findLocal
from icecap.base.util import openLocal, getNode, getReplicaAddr
from icecap.base.rep_log import RepLog

class File(idemo.File):
    """A replicated file store for small files.

    Files are stored under ``<local-data>/files``, with replication data
    under ``<local-data>/files/.rep``.

    .. note:: Work in progress. 

    :param env: server environment
    """
    def __init__(self, env):
        self._env = env
        self._log = RepLog(env, 'files/.rep')
        self._peers = None

    def _getPeers(self):
        if self._peers is None:
            peers = findLocal(self._env, self._proxy)[1]
            self._peers = [{'addr':str(p), 'proxy':p, 'method':'update'} for p in peers]
        return self._peers

    def read(self, path, curr=None):
        """Get the contents of the specified file as a string.

        :param path: the file to read
        """
        assert not path.startswith('.')
        try:
            fh = openLocal(self._env, os.path.join('files', path))
        except IOError:
            raise idemo.FileNotFound()
        return fh.read()

    def write(self, path, data, curr=None):
        """Set the contents of the specified file.

        :param path: the file to write
        :param data: the data to write
        """
        assert not path.startswith('.')
        with openLocal(self._env, os.path.join('files', path), 'w') as out:
            out.write(data)
        self._log.append(json.dumps({'path':path, 'data':data}), self._getPeers())

    def update(self, info_s, curr=None):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        info = json.loads(info_s)
        with openLocal(self._env, os.path.join('files', info['path']), 'w') as out:
            out.write(info['data'])

    def _addPeer(self, node):
        for p in self._getPeers():
            if getNode(p['addr']) == node:
                return p
        addr = getReplicaAddr(self._proxy, node)
        prx = self._env.getProxy(addr, type=self._proxy)
        p = {'addr': addr, 'proxy': prx, 'method': 'update'}
        self._peers.append(p)
        return p

    def _list(self):
        root = os.path.join(self._env.dataDir(), 'files')
        plen = len(root) + 1
        for path, dirs, files in os.walk(root):
            if '.rep' in dirs:
                dirs.remove('.rep')
            for f in files:
                yield os.path.join(path, f)[plen:]

    def list(self, curr=None):
        """Returns a list of all files."""
        return list(self._list())

    def addReplica(self, node, sync, curr=None):
        """Start replication between this replica and a new one at *node*.

        If *sync* is True, copy all files from this replica to the new one.

        :param node: node of the new replica
        :param sync: whether to copy files to the new replica
        """
        p = self._addPeer(node)
        seq = self._log.size()
        if sync:
            prx = p['proxy']
            for path in self._list():
                data = self.read(path)
                prx.update(json.dumps({'path': path, 'data': data}))
        self._log._setSeq(p['addr'], seq)
