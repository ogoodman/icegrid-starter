import json
import os
from icecap.base.util import openLocal
from icecap.data.data_log import DataLog

def toStr(s):
    return s.encode('utf8')

class RepLog(object):
    """A ``RepLog`` logs event messages and passes them to followers in order.

    Example::

        followers = [{'addr': 'fred@Foo-n1.Foo', 'method':'update'}]

        rl = RepLog(env, 'rep_log')
        rl.append('hello', followers) # calls fred.update('hello')

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
        self._log = None
        self._seq = None

    def append(self, msg, followers):
        """Appends *msg* to log and bring all *followers* up to date.

        The followers must be a list of *sink specifications*, each of which
        is a dictionary with the following keys:

        * ``addr`` - proxy string specifying a servant
        * ``method`` - method to call on the servant
        * ``arg`` - (optional) extra string to pass with every message

        :param msg: the message to pass
        :param followers: a list of sink specifications
        """
        if self._log is None:
            data_dir = os.path.join(self._env.dataDir(), self._path)
            self._log = DataLog(data_dir)
        seq = self._log.append(msg)[0]
        for sink_info in followers:
            sink_seq = self._getSeq(sink_info['addr']) or 0
            if sink_seq == seq:
                self._putMsg(sink_info, seq, msg)
            elif sink_seq < seq:
                # Simple version: catch up now if we can.
                # Really we have to apply some scheduling: back
                # off when it's not working and periodically retry
                # even when the log is not growing.
                for i, msg in self._log.iteritems(sink_seq):
                    if not self._putMsg(sink_info, i, msg):
                        break
        return seq

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
            self._setSeq(sink_id, seq + 1)
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

    def _getSeq(self, sink_id):
        if self._seq is None:
            self._loadSeq()
        return self._seq.get(sink_id)

    def _setSeq(self, sink_id, seq):
        self._seq[sink_id] = seq
        self._saveSeq()
