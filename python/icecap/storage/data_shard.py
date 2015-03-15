import os
import shutil
from icecap.base.cap_dict import CapDict
from icecap.data.data_array import DataArray
from icecap.data.file_dict import FileDict
from icecap.storage.data_relay import DataRelay

class DataShard(object):
    def __init__(self, env, path):
        self._env = env
        self._lpath = path
        self._path = os.path.join(env.dataDir(), self._lpath)

        self._data_dir = os.path.join(self._path + '/.rep')
        self._log = DataArray(self._data_dir)
        sink_store = FileDict(os.path.join(self._data_dir, 'sink'))
        extra = {'env': env, 'source': self}
        self._sinks = CapDict(sink_store, extra=extra)

    def end(self):
        return self._log.end()

    def get(self, n):
        return self._log[n]

    def _onOnline(self, addr):
        """Respond to a peer coming online."""
        if addr in self._sinks and self._log.end() > 0:
            self._sinks[addr].start()

    def isNew(self):
        return len(os.listdir(self._path)) < 2

    def peers(self):
        """Returns a list of peers this replica replicates to."""
        return self._sinks.keys()

    def addPeer(self, addr, sync):
        """Adds addr as a replica of this one, at the head of the log.

        :param addr: proxy string of the replica to add
        :param sync: (bool) whether to sync data from here to addr
        """
        if addr not in self._sinks:
            state = 'LISTING' if sync else 'REPLICATING'
            self._sinks[addr] = DataRelay(self._env, self, addr, state, self._log.end())
            if sync:
                self._sinks[addr].start()

    def removePeer(self, addr):
        """Removes addr as a replica of this one.

        :param addr: proxy string of the replica to remove
        """
        if addr in self._sinks:
            del self._sinks[addr]

    def removeData(self):
        """Removes all data from this replica."""
        shutil.rmtree(self._path)

    def append(self, msg):
        self._log.append(msg)
        for addr in self._sinks.keys():
            self._sinks[addr].start()

    def logDir(self):
        return self._data_dir
