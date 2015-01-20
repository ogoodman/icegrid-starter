import json
from icecap.base.util import openLocal
from icecap.base.rep_log import RepLog

class EventLog(object):
    """An ``EventLog`` is a persistent sequence of event messages.

    An event message is simply a string. It is up to implementations to
    decide on how event information is encoded.

    Example::

        event_log.follow('log', '{"addr": "proc@Proc-node1.Proc", "method": "update"}')
        event_log.append('A message') # returns sequence no. 0 (say)

        # The above send is equivalent to
        proc = env.getProxy('proc@Proc-node1.Proc')
        proc.update('A message')

    Subscriptions are *persistent*, i.e. they will survive a server restart.

    :param env: the environment
    :param id: the event source id
    """
    def __init__(self, env, id):
        self._env = env
        self._id = id
        self._followers = None
        self._log = RepLog(env, 'event_log/%s' % id)

    def follow(self, chan, sink, curr=None):
        """Add a follower interested receiving events sent to the specified channel.

        The follower is given by a json encoded *sink specification*. This
        has the following keys:

        * ``addr`` - proxy string specifying a servant
        * ``method`` - method to call on the servant
        * ``arg`` - (optional) extra string to pass with every message

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

    def append(self, msg):
        """Appends a message to the log and passes it to all 'log' followers.

        :param msg: (str) the message to log and pass on
        """
        if self._followers is None:
            self._load_followers()
        return self._log.append(msg, self._followers.get('log' ,{}).values())

    def _load_followers(self):
        try:
            fh = openLocal(self._env, 'event_log/%s/followers' % self._id)
            self._followers = json.load(fh)
        except IOError:
            self._followers = {}

    def _save_followers(self):
        with openLocal(self._env, 'event_log/%s/followers' % self._id, 'w') as out:
            json.dump(self._followers, out)
