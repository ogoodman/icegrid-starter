import json
import os
import sys
from icecap import idemo
from icecap.base.antenna import Antenna, notifyOnline
from icecap.base.master import findLocal
from icecap.base.util import openLocal, getAddr
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
        self._peers_added = False
        env.subscribe('online', self._onOnline)

    def _addPeer(self, prx):
        if isinstance(prx, basestring):
            addr = prx
            prx = self._env.getProxy(addr)
        else:
            addr = getAddr(prx)
        if not self._log.hasSink(addr):
            self._log.addSink({'addr': addr, 'method': 'update'})
        if self._log.getSeq(addr) is not None:
            return
        # FIXME: sync should be true iff this server is the master.
        sync = self._env.serverId() == 'SmallFS-node1'
        seq = self._log.size()
        if seq > 0 and sync:
            for path in self._list():
                data = self.read(path)
                prx.update(json.dumps({'path': path, 'data': data}))
        self._log.setSeq(addr, seq)

    def _addPeers(self):
        if not self._peers_added:
            for p in findLocal(self._env, self._proxy)[1]:
                self._addPeer(p)
            self._peers_added = True

    def _onOnline(self, server_id):
        """Respond to a peer coming online."""
        server, node = server_id.split('-', 1)
        if server != self._env.serverId().split('-', 1)[0]:
            return # nothing to do with us.
        addr = 'file@%s.%sRep' % (server_id, server)
        if not self._log.hasSink(addr):
            self._addPeer(addr)
        self._log.update(addr)

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

    def list(self, curr=None):
        """Returns a list of all files."""
        return list(self._list())

def server(env):
    env.provide('file', 'SmallFSRep', File(env))
    env.provide('antenna', 'SmallFSRep', Antenna(env))
    env.onActivation(notifyOnline, env, env.serverId())
