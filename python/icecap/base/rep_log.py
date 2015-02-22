import json
import os
from icecap.base.util import openLocal
from icecap.base.cap_dict import CapDict
from icecap.data.data_log import DataLog
from icecap.data.file_dict import FileDict

class Relay(object):
    """A Relay passes messages from a DataLog to a method of a remote object.

    :param env: an environment instance
    :param log: a log to read messages from
    :param pos: position in the log to start from
    :param addr: proxy string of a remote object
    :param method: method of the remote object to pass messages to
    :param arg: (optional) extra string argumen to pass with each message
    """

    serialize = ('pos', 'addr', 'method', 'arg')

    def __init__(self, env, log, pos, addr, method, arg=None):
        self._env = env
        self._log = log
        self._pos = pos
        self._addr = addr
        self._method = method
        self._arg = arg
        self._remote = None
        self._updating = False

    def put(self, seq=None, msg=None):
        """Wake the relay to start sending messages.

        The ``Relay`` always starts from its recorded position taking
        messages from the log, passing them to the remote object, and then
        updating and saving its new position.

        The *seq* and *msg*, if supplied, must be the item most recently
        appended to the log. If *seq* happens to match our position then *msg*
        can be passed directly without reading from the log.

        :param seq: (optional) position of last message in the log
        :param msg: (optional) the last message in the log
        """
        if self._updating:
            return
        self._updating = True
        if seq is None:
            seq = self._log.last() or 0
        try:
            if msg is not None and self._pos == seq:
                self._putMsg(seq, msg)
            elif self._pos <= seq:
                for i, msg in self._log.iteritems(self._pos):
                    if not self._putMsg(i, msg):
                        break
        finally:
            self._updating = False

    def _putMsg(self, seq, msg):
        try:
            if self._remote is None:
                proxy = self._env.getProxy(self._addr)
                self._remote = getattr(proxy, self._method)
            if self._arg is None:
                self._remote(msg)
            else:
                self._remote(msg, self._arg)
            self._pos = seq + 1
            self._save(self)
            return True
        except:
            return False

class RepLog(object):
    """A ``RepLog`` logs event messages and passes them to followers in order.

    Example::

        rl = RepLog(env, 'rep_log')
        rl.addSink({'pos': 0, 'addr': 'fred@Foo-n1.Foo', 'method': 'update'})
        rl.append('hello') # calls fred.update('hello')

    Each follower's position in the log is updated after the message is passed.

    If any exception occurs while passing a message to a follower,
    the followers position is not updated. Next time the follower appears
    in an append call, we attempt to pass all previously unsuccessfully passed
    messages.

    :param env: an environment
    :param path: local directory for log files and sinks
    """
    def __init__(self, env, path):
        self._env = env
        self._path = path
        data_dir = os.path.join(env.dataDir(), path)
        self._log = DataLog(data_dir)
        sink_store = FileDict(os.path.join(data_dir, 'sink'))
        self._sinks = CapDict(sink_store, extra={'env': env, 'log': self._log})

    def getSink(self, addr):
        """Returns the specified sink, if present, else None.

        :param addr: the address (sink_id) of the sink to get
        """
        return self._sinks.get(addr)

    def hasSink(self, addr):
        """Returns True if the specified sink is present.

        :param addr: the address (sink_id) of the sink to test
        """
        return addr in self._sinks

    def sinks(self):
        """Returns a list of sink addresses."""
        return self._sinks.keys()

    def addSink(self, sink_info):
        """Adds a sink at the specified sequence number.

        A *sink specification* is a dictionary with the following keys:

        * ``pos`` - position in log from which the sink should start
        * ``addr`` - proxy string specifying a servant
        * ``method`` - method to call on the servant
        * ``arg`` - (optional) extra string to pass with every message

        Returns False (and does not change anything) if the sink is
        already present. Returns True if the sink was added.

        :param sink_info: (dict) a sink specification
        :param seq: (int) sequence number
        """
        addr = sink_info['addr']
        if addr in self._sinks:
            return False
        sink_info.update(self._sinks._extra)
        self._sinks[addr] = Relay(**sink_info)
        return True

    def removeSink(self, addr):
        """Removes the specified sink.

        Returns True if the sink was found and removed.

        :param addr: the address (sink_id) of the sink to remove
        """
        if addr not in self._sinks:
            return False
        del self._sinks[addr]
        return True

    def append(self, msg):
        """Appends *msg* to log and push it to all sinks.

        :param msg: the message to pass
        """
        seq = self._log.append(msg)[0]
        for addr in self._sinks.keys():
            self._sinks[addr].put(seq, msg)
        return seq

    def size(self):
        """Returns the number of items in the log.

        Items are numbered from 0 so the size is also the next sequence number.
        """
        last = self._log.last()
        return 0 if last is None else last + 1

    def update(self, addr):
        """Brings the specified sink up-to-date (if possible).

        :param addr: the sink to push updates to
        """
        size = self.size()
        if size == 0:
            return
        self._sinks[addr].put()

    def setSeq(self, addr, seq):
        """Set the sequence number of the specified sink.

        :param sink_id: the sink whose sequence number is to be updated
        :param seq: the index of the next log entry to be pushed
        """
        sink = self._sinks[addr]
        sink._pos = seq
        sink._save(sink)

    def getSeq(self, addr):
        """Get the sequence number of the specified sink.

        Returns None if no such sink exists.

        :param addr: the sink whose sequence number is required
        """
        return self._sinks[addr]._pos
