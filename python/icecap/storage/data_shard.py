import os
import shutil
from icecap.base.cap_dict import CapDict
from icecap.data.data_array import DataArray
from icecap.data.file_dict import FileDict
from icecap.storage.data_relay import DataRelay

class DataShard(object):
    """Handles replication for a single data-shard. Subclasses add operations
    for specific data types.

    It provides an iterface for logging data updates and reading back those logs::

        ds = DataShard(env, path)
        ds.append(msg)
        ds.end()  # one past the last logged data update
        ds.get(i) # get the i-th logged data update

    A persistent collection of DataRelay objects pass these updates to DataNode peers.

    Subclasses must provide methods for listing and dumping existing data::

        ds.list()     # -> iterable of paths in the shard
        ds.dump(path) # -> seq, iter representing a snapshot of the item at path

    It also proves an interface to the DataNode objects whose task
    is to add and remove DataRelays (peers)::

        ds.isNew()
        ds.peers()
        ds.addPeer(addr)
        ds.removePeer(addr)
        ds.removeData()

    :param env: an environment object
    :param path: the relative local path at which to store data and logs
    """
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
        """One past the index of the last log entry, or 0 if the log is empty."""
        return self._log.end()

    def get(self, n):
        """Gets the *n*-th log entry as a string.

        :param n: index of the log entry to get
        """
        return self._log[n]

    def _onOnline(self, addr):
        """Respond to a peer coming online."""
        if addr in self._sinks and self._log.end() > 0:
            self._sinks[addr].start()

    def isNew(self):
        """True if no data has yet been stored in this shard."""
        return len(os.listdir(self._path)) < 2

    def peers(self):
        """Returns a list of DataNode proxy addresses this replica replicates to."""
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
        """Append *msg* to the replication log.

        :param msg: a message to add to the log
        """
        self._log.append(msg)
        for addr in self._sinks.keys():
            self._sinks[addr].start()

    def logDir(self):
        """Returns the path of the replication log directory.

        This is used by the DataRelay to create a temporary listing of the shard
        while copying data to a new shard.
        """
        return self._data_dir
