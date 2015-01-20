import json
import sys
import traceback
from icecap import ibase
from icecap.base.util import openLocal

def toStr(s):
    return s.encode('utf8')

class EventSource(ibase.EventSource):
    """An ``EventSource`` is a servant which emits event messages.

    An event message is simply a string. It is up to implementations to
    decide on how event information is encoded.

    :param env: the environment
    :param id: the event source id
    """
    def __init__(self, env, id):
        self._env = env
        self._id = id
        self._followers = None

    def follow(self, chan, sink, curr=None):
        """Add a follower interested receiving events sent to the specified channel.

        The follower is given by a json encoded *sink specification*. This
        has the following keys:

        * ``addr`` - proxy string specifying a servant
        * ``method`` - method to call on the servant
        * ``arg`` - (optional) extra string to pass with every message

        Example::

            events.follow('foo', '{"addr": "log@Log-node1.Log", "method": "append"}')
            events.send('foo', 'A message')

            # the above send is equivalent to
            log = env.getProxy('log@Log-node1.Log')
            log.append('A message')

        Subscriptions are *persistent*, i.e. they will survive a server restart.

        :param chan: (str) event channel
        :param sink: (json) sink specification
        """
        if self._followers is None:
            self._load_followers()
        if chan not in self._followers:
            self._followers[chan] = {}
        chan_followers = self._followers[chan]
        sink_info = json.loads(sink)
        sink_id = sink_info['addr']
        chan_followers[sink_id] = sink_info
        self._save_followers()

    def unfollow(self, chan, addr, curr=None):
        """Stops a follower receiving events sent to the specified channel.

        :param chan: the channel to remove a follower from
        :param addr: the proxy string of the follower
        """
        if self._followers is None:
            self._load_followers()
        if chan not in self._followers:
            return
        self._followers[chan].pop(addr, None)
        self._save_followers()

    def send(self, chan, msg, curr=None):
        """Send *msg* to all followers on the specified channel.

        :param chan: the channel to send a message on
        :param msg: (str) the message to send
        """
        if self._followers is None:
            self._load_followers()
        if chan not in self._followers:
            return
        for sink_info in self._followers[chan].values():
            try:
                if 'proxy' not in sink_info:
                    sink_info['proxy'] = self._env.getProxy(toStr(sink_info['addr']))
                proxy = sink_info['proxy']
                method = getattr(proxy, toStr(sink_info['method']))
                arg = sink_info.get('arg')
                if arg is None:
                    method(msg)
                else:
                    method(msg, toStr(arg))
            except:
                traceback.print_exc()

    def _load_followers(self):
        try:
            fh = openLocal(self._env, 'events/%s/followers' % self._id)
            self._followers = json.load(fh)
        except IOError:
            self._followers = {}

    def _save_followers(self):
        with openLocal(self._env, 'events/%s/followers' % self._id, 'w') as out:
            json.dump(self._followers, out)
