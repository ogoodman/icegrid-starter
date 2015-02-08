import json
import os
from icecap.base.util import openLocal
from icecap.data.data_log import DataLog

def toStr(s):
    return s.encode('utf8')

class RepLog(object):
    """A ``RepLog`` logs event messages and passes them to followers in order.

    Example::

        rl = RepLog(env, 'rep_log')
        rl.addSink({'addr': 'fred@Foo-n1.Foo', 'method': 'update'})
        rl.append('hello') # calls fred.update('hello')

    Each follower's position in the log is updated after the message is passed.

    If any exception occurs while passing a message to a follower,
    the followers position is not updated. Next time the follower appears
    in an append call, we attempt to pass all previously unsuccessfully passed
    messages.

    :param env: an environment
    :param path: local directory for log files and position store
    """
    def __init__(self, env, path):
        self._env = env
        self._path = path
        self._seq = None
        self._sinks = None
        data_dir = os.path.join(env.dataDir(), path)
        self._log = DataLog(data_dir)
        self._updating = None

    def _getSinks(self):
        if self._sinks is None:
            sink_file = os.path.join(self._env.dataDir(), self._path, 'sinks')
            try:
                self._sinks = json.load(open(sink_file))
            except IOError:
                self._sinks = []
        return self._sinks

    def _saveSinks(self):
        sinks = []
        for s in self._getSinks():
            s_copy = dict(s)
            s_copy.pop('proxy', None)
            sinks.append(s_copy)
        sink_file = os.path.join(self._env.dataDir(), self._path, 'sinks')
        with open(sink_file, 'w') as out:
            json.dump(sinks, out)

    def getSink(self, addr):
        """Returns the specified sink, if present, else None.

        :param addr: the address (sink_id) of the sink to get
        """
        for s in self._getSinks():
            if s['addr'] == addr:
                return s
        return None

    def hasSink(self, addr):
        """Returns True if the specified sink is present.

        :param addr: the address (sink_id) of the sink to test
        """
        for s in self._getSinks():
            if s['addr'] == addr:
                return True
        return False

    def addSink(self, sink_info):
        """Adds a sink at the specified sequence number.

        A *sink specification* is a dictionary with the following keys:

        * ``addr`` - proxy string specifying a servant
        * ``method`` - method to call on the servant
        * ``arg`` - (optional) extra string to pass with every message

        Returns False (and does not change anything) if the sink is
        already present. Returns True if the sink was added.

        :param sink_info: (dict) a sink specification
        :param seq: (int) sequence number
        """
        if self.hasSink(sink_info['addr']):
            return False
        self._getSinks().append(sink_info)
        self._saveSinks()
        return True

    def removeSink(self, addr):
        """Removes the specified sink.

        Returns True if the sink was found and removed.

        :param addr: the address (sink_id) of the sink to remove
        """
        for i, s in enumerate(list(self._getSinks())):
            if s['addr'] == addr:
                del self._sinks[i]
                return True
        return False

    def append(self, msg):
        """Appends *msg* to log and push it to all sinks.

        :param msg: the message to pass
        """
        seq = self._log.append(msg)[0]
        for sink_info in self._getSinks():
            self._update(sink_info, seq + 1, msg)
        return seq

    def size(self):
        """Returns the number of items in the log.

        Items are numbered from 0 so the size is also the next sequence number.
        """
        last = self._log.last()
        return 0 if last is None else last + 1

    def _update(self, sink_info, size, msg):
        addr = sink_info['addr']
        if self._updating == addr:
            return
        self._updating = addr
        try:
            sink_seq = self.getSeq(addr)
            if sink_seq is None:
                if size > 1:
                    return
                sink_seq = 0
            if msg is not None and size == sink_seq + 1:
                self._putMsg(sink_info, sink_seq, msg)
            elif sink_seq < size:
                for i, msg in self._log.iteritems(sink_seq):
                    if not self._putMsg(sink_info, i, msg):
                        break
        finally:
            self._updating = None

    def update(self, addr):
        """Brings the specified sink up-to-date (if possible).

        :param addr: the sink to push updates to
        """
        size = self.size()
        if size == 0:
            return
        sink_info = self.getSink(addr)
        if sink_info is None:
            return
        self._update(sink_info, size, None)

    def _putMsg(self, sink_info, seq, msg):
        try:
            sink_id = toStr(sink_info['addr'])
            if 'proxy' not in sink_info:
                sink_info['proxy'] = self._env.getProxy(sink_id)
            proxy = sink_info['proxy']
            method = getattr(proxy, toStr(sink_info['method']))
            arg = sink_info.get('arg')
            if arg is None:
                method(msg)
            else:
                method(msg, toStr(arg))
            self.setSeq(sink_id, seq + 1)
            return True
        except:
            return False

    def _loadSeq(self):
        try:
            fh = openLocal(self._env, '%s/seq' % self._path)
            self._seq = json.load(fh)
        except IOError:
            self._seq = {}

    def _saveSeq(self):
        with openLocal(self._env, '%s/seq' % self._path, 'w') as out:
            json.dump(self._seq, out)

    def getSeq(self, sink_id):
        """Get the sequence number of the specified sink.

        Returns None if no such sink exists.

        :param sink_id: the sink whose sequence number is required
        """
        if self._seq is None:
            self._loadSeq()
        return self._seq.get(sink_id)

    def setSeq(self, sink_id, seq):
        """Set the sequence number of the specified sink.

        :param sink_id: the sink whose sequence number is to be updated
        :param seq: the index of the next log entry to be pushed
        """
        if self._seq is None:
            self._loadSeq()
        self._seq[sink_id] = seq
        self._saveSeq()

    def removeSeq(self, sink_id):
        """Erases the recorded sequence number of the specified sink.

        :param sink_id: the sink whose sequence number is to be discarded
        """
        if self._seq is None:
            self._loadSeq()
        if self._seq.pop(sink_id, None) is not None:
            self._saveSeq()
