"""The purpose of a DataRelay is to copy data from a master to a slave DataNode shard.

It can 

* copy data from an existing shard to a new empty one, and
* replicate data between two existing shards.

When a DataRelay finishes copying data to a new shard, it switches automatically
to replication.

A DataRelay has three basic states:

* ``LISTING`` - preparing to copy data,
* ``COPYING`` - copying data,
* ``REPLICATING`` - keeping data in sync.

It is a persistent object and must be stored in a CapDict so it can save its state
with every change. Its full state consists of its state, as above, and:

* ``pos`` - an int saying where it is in the source replication log,
* ``copy_pos`` - an int (only used in the ``COPYING`` state) saying where it is in the
  list of items to copy.

It also stores a list of items to be copied in a local file. This is written while
in the ``LISTING`` state and then read during the ``COPYING`` state.

It requires a source object with methods 

* ``source.list()``, yielding a sequence of paths,
* ``source.dump(path)``, returning ``(seq, iter)``,
* ``source[n]``, and
* ``source.end()``, 

and a target object with an asynchronous

* ``target.begin_update(msg, on_ok, on_err)``

method.

If started in the ``LISTING`` state, it sets its ``pos`` to the end of the replication
log, ``len(source)`` then starts a thread copying the output of ``source.list()``
to the local listing file. While the listing thread is running it copies updates
from the source to the target. The non-persistent ``._in_update`` flag is set before we
begin an update and cleared if there are no more updates to perform.

Once the listing is complete the state transitions to ``COPYING`` and ``copy_pos`` is set
to 0. If an update may be in progress, i.e. ``._in_update`` is set, we wait
until the update is finished. We then cycle through the following steps:

* read a ``path`` from the listing,
* call ``source.dump(path)`` to obtain a sequence number ``seq`` in the replication log
  and iterable of updates needed to replicate ``path``,
* apply updates from ``source`` until we reach ``seq``, updating ``pos`` as we go,
* apply updates from the earlier dump,
* increment the ``copy_pos``.

When there are no more lines to read from the listing, we transition to state
``REPLICATING`` and remove the listing file. In the replicating state we simply
apply updates from the ``source``, incrementing ``pos`` with each one.
"""

import os
import sys
import threading
import Ice

class DataRelay(object):
    """A DataRelay synchronises data from *source* to *target*.

    :param env: an environment object
    :param source: a DataNode shard and replication log
    :param addr: address of a DataNode to receive data and/or updates
    :param state: (str) one of ``LISTING``, ``COPYING`` or ``REPLICATING``
    :param pos: (int) position in the *source* replication log
    :param copy_pos: (int/None) position in the listing while copying
    :param target: (optional) a DataNode shard to receive data and/or updates
    """
    serialize = ('addr', 'state', 'pos', 'copy_pos')

    def __init__(self, env, source, addr, state, pos=None, copy_pos=None, target=None):
        self._source = source
        self._addr = addr
        self._target = env.getProxy(addr) if target is None else target
        self._listing = os.path.join(source.logDir(), 'DATALIST')
        self._state = state
        self._pos = pos
        self._copy_pos = copy_pos
        self._started = False
        self._in_update = False
        self._listing_fh = None
        self._dump_seq = None
        self._dump = None
        self._lock = threading.Lock()
        self._calls = []

    def _do(self, func, *args):
        self._calls.append((func, args))

    def run(self):
        while self._calls:
            func, args = self._calls.pop(0)
            func(*args)

    def start(self):
        """Starts updates or any other activity the DataRelay is expected to perform.

        This should be called once when the server hosting ``source`` is started
        and again whenever new data is appended to ``source``.
        """
        with self._lock:
            if self._started:
                start_updates = self._state != 'COPYING' and not self._in_update
            else:
                if self._state == 'LISTING':
                    if self._pos is None:
                        self._pos = self._source.end()
                        self._save(self)
                    self._do(self._listSource)
                    start_updates = True
                elif self._state == 'COPYING':
                    self._do(self._copyOne)
                    start_updates = False
                else:
                    start_updates = True
                self._started = True
            if start_updates:
                self._in_update = True

        if start_updates:
            self._pushNext()
        self.run()

    def _listSource(self):
        """Runs in a thread making a listing of the source during the ``LISTING`` state."""
        with open(self._listing, 'w') as out:
            for path in self._source.list():
                out.write(path + '\n')
        with self._lock:
            self._state = 'COPYING'
            self._copy_pos = 0
            self._save(self)
            self._do(self._copyOne)

    def _copyOne(self):
        """Reads a path from the listing and calls ``source.dump(path)`` in the ``COPYING`` state."""
        with self._lock:
            if self._in_update:
                return
            try:
                if self._listing_fh is None:
                    self._listing_fh = open(self._listing)
                    for i in xrange(self._copy_pos):
                        self._listing_fh.next()
                path = self._listing_fh.next().rstrip('\n')
            except StopIteration:
                self._state = 'REPLICATING'
                self._listing_fh = None
                self._copy_pos = None
                self._save(self)
                os.unlink(self._listing)
            else:
                self._dump_seq, self._dump = self._source.dump(path)
            self._in_update = True

        self._pushNext()

    def _onOk(self, *_):
        """Runs whenever an update from the source is successfully applied."""
        with self._lock:
            self._pos = self._pos + 1
            self._save(self)
        self._pushNext()

    def _onOkNoInc(self, *_):
        """Runs whenever an update from a dumped data item has been successfully applied."""
        self._pushNext()

    def _onErr(self, exc):
        """Runs whenever an error occurs applying any kind of update to the target."""
        if not isinstance(exc, Ice.NoEndpointException):
            print >>sys.stderr, 'Exception from update:', exc
        self._in_update = False

    def _pushNext(self):
        """Begins the next update on the target, or runs ``._copyOne`` to get the next update.

        When not in ``COPYING`` state this calls ``target.begin_update()`` with the next
        update from the source. If no more updates are available it resets then ``._in_update``
        flag. No further activity will take place until ``.start()`` is called again.

        When in ``COPYING`` state it will copy an update from the source if we have not
        reached the next snapshot ``seq`` number, copy an update from the most recent snapshot
        if we have reached ``seq``, or start a new ``._copyOne`` call if we've finished
        copying a snapshot.
        """
        with self._lock:
            assert self._in_update
            msg = None
            if self._state == 'COPYING':
                if self._dump is None:
                    self._in_update = False
                    self._do(self._copyOne)
                elif self._pos < self._dump_seq:
                    msg = self._source.get(self._pos)
                    on_ok = self._onOk
                else:
                    try:
                        msg = self._dump.next()
                        on_ok = self._onOkNoInc
                    except StopIteration:
                        self._copy_pos += 1
                        self._save(self)
                        self._in_update = False
                        self._do(self._copyOne)
            else:
                if self._pos < self._source.end():
                    msg = self._source.get(self._pos)
                    on_ok = self._onOk
                else:
                    self._in_update = False

        if msg is not None:
            self._target.begin_update(msg, on_ok, self._onErr)
