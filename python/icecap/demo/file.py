import json
import os
from icecap import idemo
from icecap.base.master import findLocal
from icecap.base.util import openLocal
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
        if self._peers is None:
            peers = findLocal(self._env, self._proxy)[1]
            self._peers = [{'addr':str(p), 'proxy':p, 'method':'update'} for p in peers]
            print self._peers
        self._log.append(json.dumps({'path':path, 'data':data}), self._peers)

    def update(self, info_s, curr=None):
        """For replication only: applies the supplied json-encoded update.

        :param info_s: a json encoded update
        """
        info = json.loads(info_s)
        with openLocal(self._env, os.path.join('files', info['path']), 'w') as out:
            out.write(info['data'])
